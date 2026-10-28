"""No executable research defaults; new scene/sensor choices need an exact manifest."""
from dataclasses import dataclass,asdict
import json,re
import numpy as np
from ..avoidance.contracts import Settings as MotionSettings,vector,positive
from .geometry import Part
from .pose import unit_quaternion

@dataclass(frozen=True)
class View:
    id:str
    quaternion:tuple
    width:int
    height:int
    focal_px:float
    def __post_init__(self):
        if not re.fullmatch('[a-z][a-z0-9_]{0,39}',self.id):raise ValueError('Invalid view ID')
        unit_quaternion(self.quaternion)
        if type(self.width) is not int or type(self.height) is not int or not 4<=self.width<=512 or not 4<=self.height<=512:raise ValueError('View dimensions outside bounded renderer contract')
        positive(self.focal_px,'focal_px')

@dataclass(frozen=True)
class Vision:
    target_rgb:tuple
    color_distance:float
    min_component_pixels:int
    range_pixel_uncertainty:float
    max_cone_error_rad:float
    seam_merge_angle_rad:float
    association_distance:float
    association_ambiguity:float
    max_gap_ms:float
    def __post_init__(self):
        if len(self.target_rgb)!=3 or any(type(v) is not int or not 0<=v<=255 for v in self.target_rgb):raise ValueError('Declared visual color prior required')
        for n in ('color_distance','range_pixel_uncertainty','max_cone_error_rad','seam_merge_angle_rad','association_distance','association_ambiguity','max_gap_ms'):positive(getattr(self,n),n)
        if type(self.min_component_pixels) is not int or self.min_component_pixels<=0:raise ValueError('Component size must be explicit')

@dataclass(frozen=True)
class RoomConfig:
    motion:MotionSettings
    views:tuple
    vision:Vision
    cruise_body_velocity:tuple
    max_heading_rate_rad_s:float
    recovery_ms:int
    known_static_map:bool
    allow_cruise_when_no_target_visible:bool
    room_color:tuple
    def __post_init__(self):
        if self.motion.dimensions!=3:raise ValueError('Room physics requires 3D')
        if not 1<=len(self.views)<=6 or len({v.id for v in self.views})!=len(self.views):raise ValueError('1–6 uniquely calibrated views required')
        if len({(v.width,v.height) for v in self.views})!=1:raise ValueError('Synchronized views must have identical image dimensions')
        if np.linalg.norm(vector(self.cruise_body_velocity,3))>self.motion.escape_speed_max:raise ValueError('Cruise exceeds inherited speed cap')
        positive(self.max_heading_rate_rad_s,'heading limit')
        if type(self.recovery_ms) is not int or self.recovery_ms<0 or type(self.known_static_map) is not bool or type(self.allow_cruise_when_no_target_visible) is not bool:raise ValueError('Explicit recovery/map contract required')
        if len(self.room_color)!=3 or any(type(v) is not int or not 0<=v<=255 for v in self.room_color):raise ValueError('Room material required')
    def public(self):
        result=self.motion.public();result.update(room_flight=True,sensor_profile='engineering_surround_color_and_size_prior',camera_rig=[asdict(v) for v in self.views],vision=asdict(self.vision),cruise_body_velocity=self.cruise_body_velocity,max_heading_rate_rad_s=self.max_heading_rate_rad_s,recovery_ms=self.recovery_ms,known_static_map=self.known_static_map,allow_cruise_when_no_target_visible=self.allow_cruise_when_no_target_visible,room_color=self.room_color,neural_role='diagnostic_front_view_only',physics_model='kinematic_translation_and_yaw_not_aerodynamic')
        return result

@dataclass(frozen=True)
class Solid:
    id:str
    parts:tuple
    keyframes:tuple
    def __post_init__(self):
        if not re.fullmatch('[a-z][a-z0-9_]{0,79}',self.id) or not self.parts or len(self.parts)>16:raise ValueError('Named bounded compound solid required')
        previous=-1
        for i,k in enumerate(self.keyframes):
            if set(k)!={'time_ms','position'} or type(k['time_ms']) is not int or k['time_ms']<0 or k['time_ms']<=previous:raise ValueError('Invalid physical keyframe clock')
            if i==0 and k['time_ms']!=0:raise ValueError('Motion needs a time-zero state')
            vector(k['position'],3);previous=k['time_ms']
        if not self.keyframes:raise ValueError('Missing object state')
    def position(self,t):
        times=[k['time_ms'] for k in self.keyframes];i=int(np.searchsorted(times,t,side='right'))-1;i=max(0,i)
        if i==len(times)-1:return np.asarray(self.keyframes[i]['position'],dtype=float)
        alpha=(t-times[i])/(times[i+1]-times[i]);return np.asarray(self.keyframes[i]['position'])*(1-alpha)+np.asarray(self.keyframes[i+1]['position'])*alpha
    def velocity(self,t):
        times=[k['time_ms'] for k in self.keyframes];i=max(0,int(np.searchsorted(times,t,side='right'))-1)
        if i==len(times)-1:return np.zeros(3)
        return (np.asarray(self.keyframes[i+1]['position'])-self.keyframes[i]['position'])/((times[i+1]-times[i])/1000)
    def public(self):return dict(id=self.id,parts=[p.public() for p in self.parts],keyframes=self.keyframes)

@dataclass(frozen=True)
class Scene:
    scenario_id:str
    fly_position:tuple
    fly_velocity:tuple
    fly_quaternion:tuple
    static_solids:tuple
    dynamic_solids:tuple
    encounters:tuple
    def validate(self,c):
        if not re.fullmatch('[a-z][a-z0-9_]{0,79}',self.scenario_id):raise ValueError('Invalid scene ID')
        vector(self.fly_position,3);vector(self.fly_velocity,3);unit_quaternion(self.fly_quaternion)
        if np.linalg.norm(self.fly_velocity)>c.motion.escape_speed_max:raise ValueError('Initial speed exceeds cap')
        if len(self.static_solids)+len(self.dynamic_solids)>64:raise ValueError('Room solid capacity exceeded')
        ids=[s.id for s in (*self.static_solids,*self.dynamic_solids)]
        if len(set(ids))!=len(ids):raise ValueError('Unique evaluator object IDs required')
        for e in self.encounters:
            if set(e)!={'id','start_ms','end_ms','object_ids'} or not 0<=e['start_ms']<e['end_ms']<=c.motion.duration_ms or not e['object_ids'] or not set(e['object_ids'])<=set(ids):raise ValueError('Explicit evaluator encounter windows required')
        for s in self.static_solids:
            if len(s.keyframes)!=1:raise ValueError('Static furniture cannot have a motion script')
        return self
    def public(self):return dict(scenario_id=self.scenario_id,fly_position=self.fly_position,fly_quaternion=self.fly_quaternion,static_solids=[s.public() for s in self.static_solids],dynamic_solids=[s.public() for s in self.dynamic_solids],encounters=self.encounters)

MODELS=('ordinary_motion','approach_trigger','surround_avoidance')
def parse_config(d):
    d=dict(d);d['motion']=MotionSettings(**d['motion']);d['views']=tuple(View(**v) for v in d['views']);d['vision']=Vision(**d['vision']);return RoomConfig(**d)
def parse_solid(d):return Solid(d['id'],tuple(Part(**p) for p in d['parts']),tuple(d['keyframes']))
def parse_scene(d,c):
    d=dict(d)
    for k in ('static_solids','dynamic_solids'):d[k]=tuple(parse_solid(s) for s in d[k])
    return Scene(**d).validate(c)
def load_protocol(path):
    d=json.loads(__import__('pathlib').Path(path).read_text())
    if d['schema']!='room_flight_protocol_1.0' or d['partition']!='engineering_development' or d['models']!=list(MODELS):raise ValueError('Room protocol scope differs')
    c=parse_config(d['settings']);scenes=[parse_scene(s,c) for s in d['scenes']]
    if not scenes or len(scenes)*3>24 or len({s.scenario_id for s in scenes})!=len(scenes):raise ValueError('Unique scenes and 24-attempt ceiling required')
    if not 0<d['max_stage_seconds']<=1800 or not 0<d['max_output_bytes']<=1024**3:raise ValueError('Resource budget exceeds approved plan')
    return d,c,scenes
