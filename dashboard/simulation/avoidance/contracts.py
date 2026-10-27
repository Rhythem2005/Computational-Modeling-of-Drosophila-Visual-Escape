"""Explicit protocol contracts. New physical/control choices have no hidden defaults."""
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib, json, math, re
import numpy as np

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def vector(value, dimension):
    result=np.asarray(value,dtype=np.float64)
    if result.shape!=(dimension,) or not np.isfinite(result).all():raise ValueError('Invalid finite coordinate vector')
    return result

def positive(value,name):
    if isinstance(value,bool) or not isinstance(value,(float,int)) or not math.isfinite(value) or value<=0:raise ValueError(name+' must be finite and positive')

@dataclass(frozen=True)
class Settings:
    dimensions:int
    duration_ms:int
    bounds:tuple
    fly_radius:float
    object_radius_prior:float
    camera_width:int
    camera_height:int
    camera_fps:int
    camera_center_px:tuple
    camera_focal_px:float
    camera_near_depth:float
    background_uint8:int
    object_uint8:int
    min_contrast_uint8:int
    actuation_delay_ms:int
    escape_speed_max:float
    escape_acceleration_max:float
    prediction_horizon_ms:int
    candidate_directions:tuple
    association_gate_px:float
    association_ambiguity_px:float
    max_radius_fraction_change:float
    max_shape_error_fraction:float
    clearance_margin:float
    max_observation_age_ms:int
    success_final_clearance_min:float

    def __post_init__(self):
        if type(self.dimensions) is not int or self.dimensions not in (2,3):raise ValueError('Only planar or genuine 3-D coordinates are supported')
        for name in ('duration_ms','camera_width','camera_height','camera_fps','prediction_horizon_ms','max_observation_age_ms'):
            if type(getattr(self,name)) is not int or getattr(self,name)<=0:raise ValueError(name+' must be a positive integer')
        if type(self.actuation_delay_ms) is not int or self.actuation_delay_ms<0:raise ValueError('Invalid actuation delay')
        for name in ('fly_radius','object_radius_prior','camera_focal_px','camera_near_depth','escape_speed_max','escape_acceleration_max','association_gate_px','association_ambiguity_px','max_radius_fraction_change','max_shape_error_fraction','success_final_clearance_min'):
            positive(getattr(self,name),name)
        if self.clearance_margin<0 or not math.isfinite(self.clearance_margin):raise ValueError('Invalid safety margin')
        for name in ('background_uint8','object_uint8','min_contrast_uint8'):
            if type(getattr(self,name)) is not int or not 0<=getattr(self,name)<=255:raise ValueError('Invalid pixel constant')
        if self.min_contrast_uint8==0 or abs(self.background_uint8-self.object_uint8)<self.min_contrast_uint8:raise ValueError('Insufficient image contrast')
        bounds=np.asarray(self.bounds,dtype=float)
        if bounds.shape!=(self.dimensions,2) or not np.isfinite(bounds).all() or np.any(bounds[:,1]-bounds[:,0]<=2*self.fly_radius):raise ValueError('Invalid bounds')
        center=vector(self.camera_center_px,2)
        if not (0<=center[0]<self.camera_width and 0<=center[1]<self.camera_height):raise ValueError('Camera center outside image')
        if self.prediction_horizon_ms>self.duration_ms or len(self.candidate_directions)>64:raise ValueError('Prediction/candidate budget exceeded')
        if not self.candidate_directions:raise ValueError('Explicit reviewed candidate directions required')
        for direction in self.candidate_directions:
            d=vector(direction,self.dimensions)
            if not np.isclose(np.linalg.norm(d),1,atol=1e-12):raise ValueError('Candidate directions must be unit vectors')

    def public(self):
        d=asdict(self)
        d.update(world_dimension=self.dimensions,world_units='abstract',world_dt_ms=1,
                 coordinate_semantics='x_right_y_forward_z_up',physics_model='bounded_acceleration_kinematic',
                 bounds_xy=list(self.bounds[:2]),duration_ms=self.duration_ms,
                 frozen_encoder_multiobject_validated=False)
        return d

@dataclass(frozen=True)
class Scenario:
    scenario_id:str
    fly_position:tuple
    fly_velocity:tuple
    obstacles:tuple

    def validate(self,c):
        if not isinstance(self.scenario_id,str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,79}',self.scenario_id) or not self.obstacles:raise ValueError('Named nonempty scenario required')
        p=vector(self.fly_position,c.dimensions);v=vector(self.fly_velocity,c.dimensions)
        if np.linalg.norm(v)>c.escape_speed_max+1e-12:raise ValueError('Initial fly exceeds speed cap')
        ids=[]
        for ob in self.obstacles:
            if set(ob)!= {'id','position','velocity','radius','onset_ms'}:raise ValueError('Unexpected object contract')
            ids.append(ob['id']);vector(ob['position'],c.dimensions);vector(ob['velocity'],c.dimensions)
            positive(ob['radius'],'radius')
            if ob['radius']!=c.object_radius_prior:raise ValueError('This reviewed observer requires the declared common radius prior')
            if type(ob['onset_ms']) is not int or not 0<=ob['onset_ms']<c.duration_ms:raise ValueError('Invalid motion onset')
        if len(set(ids))!=len(ids) or any(not isinstance(i,str) or not i for i in ids):raise ValueError('Unique object identities required')
        bounds=np.asarray(c.bounds)
        if np.any(p<=bounds[:,0]+c.fly_radius) or np.any(p>=bounds[:,1]-c.fly_radius):raise ValueError('Initial fly outside bounds')
        return self

MODELS=('no_action','simple_trigger','frozen_latched','planner_only','circuit_planner')
def load_protocol(path):
    path=Path(path);record=json.loads(path.read_text())
    if record.get('schema')!='multi_object_protocol_1.0':raise ValueError('Unsupported protocol schema')
    c=Settings(**record['settings'])
    scenarios=[Scenario(**s).validate(c) for s in record['scenarios']]
    if not scenarios or len({s.scenario_id for s in scenarios})!=len(scenarios):raise ValueError('Unique scenarios required')
    if record['models']!=list(MODELS):raise ValueError('All five comparisons must be declared in fixed order')
    if len(scenarios)*len(MODELS)>24:raise ValueError('24-episode stage cap exceeded')
    if record['partition']!='engineering_development':raise ValueError('Independent evaluation requires a separate protocol')
    if type(record.get('max_stage_seconds')) is not int or not 0<record['max_stage_seconds']<=1800:raise ValueError('Stage time cap must be explicit and at most 30 minutes')
    if type(record.get('max_output_bytes')) is not int or not 0<record['max_output_bytes']<=1024**3:raise ValueError('Output cap must be explicit and at most 1 GiB')
    if not re.fullmatch(r'[a-z][a-z0-9_]{0,79}',record['protocol_id']):raise ValueError('Invalid protocol identity')
    return record,c,scenarios

def verify_authorization(protocol,authorization):
    a=json.loads(Path(authorization).read_text())
    if a.get('status')!='APPROVED_EXACT_PROTOCOL' or a.get('protocol_sha256')!=digest(protocol):raise ValueError('Exact protocol approval missing or changed')
    if a.get('episode_cap')!=24 or a.get('training_authorized') is not False or a.get('held_out_authorized') is not False:raise ValueError('Authorization scope differs')
    return a
