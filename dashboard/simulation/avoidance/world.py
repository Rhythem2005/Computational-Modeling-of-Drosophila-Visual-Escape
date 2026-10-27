"""2-D/3-D finite-body world. Geometry is never passed to visual perception."""
from dataclasses import asdict
import numpy as np
from .contracts import vector

def swept_contact(p,d,radius):
    p=np.asarray(p,dtype=float);d=np.asarray(d,dtype=float)
    if p.shape!=d.shape or p.ndim!=1 or not np.isfinite(p).all() or not np.isfinite(d).all() or radius<=0:raise ValueError('Invalid swept segment')
    aa=float(d@d);cc=float(p@p)-radius**2
    u=0. if aa==0 else float(np.clip(-(p@d)/aa,0,1))
    clearance=float(np.linalg.norm(p+u*d)-radius)
    if cc<=0:return 0.,clearance
    if aa==0:return None,clearance
    mid=-float(p@d)/aa;perp=p+mid*d;gap=radius**2-float(perp@perp)
    tolerance=64*np.finfo(float).eps*(radius**2+float(perp@perp))
    if gap < -tolerance:return None,clearance
    entry=mid-np.sqrt(max(0.,gap)/aa)
    return (float(np.clip(entry,0,1)) if -64*np.finfo(float).eps<=entry<=1+64*np.finfo(float).eps else None),clearance

def advance_velocity(velocity,target,acceleration,dt):
    delta=target-velocity;norm=float(np.linalg.norm(delta))
    return velocity+delta*(min(1.,acceleration*dt/norm) if norm else 0.)

class World:
    def __init__(self,settings,scenario):
        self.c=settings;self.scenario=scenario.validate(settings)
        self.fly=vector(scenario.fly_position,settings.dimensions).copy();self.velocity=vector(scenario.fly_velocity,settings.dimensions).copy()
        self.obstacles=np.asarray([o['position'] for o in scenario.obstacles],dtype=np.float64)
        self.radii=np.asarray([o['radius'] for o in scenario.obstacles]);self.time_ms=0.;self.pending=[];self.target=self.velocity.copy()
        self.failure=None;self.requests=[];self.first_motion_ms=None
        if np.any(np.linalg.norm(self.obstacles-self.fly,axis=1)<=self.radii+self.c.fly_radius):raise ValueError('Initially overlapping fixture')
    @property
    def done(self):return self.failure is not None or self.time_ms>=self.c.duration_ms
    def request(self,target):
        if self.done:raise ValueError('Command after termination')
        target=vector(target,self.c.dimensions)
        if np.linalg.norm(target)>self.c.escape_speed_max+1e-12:raise ValueError('Command exceeds speed cap')
        self.pending.append((self.time_ms+self.c.actuation_delay_ms,target.copy()))
        self.requests.append(self.time_ms)
    def positions_at(self,t):
        return np.array([np.asarray(o['position'])+np.asarray(o['velocity'])*max(0,t-o['onset_ms'])/1000 for o in self.scenario.obstacles])
    def step(self):
        if self.done:raise ValueError('Step after terminal state')
        start=self.time_ms;end=min(start+1,self.c.duration_ms);dt=(end-start)/1000
        due=[v for t,v in self.pending if t<=start]
        if due:self.target=due[-1].copy()
        self.pending=[(t,v) for t,v in self.pending if t>start]
        old_fly=self.fly.copy();old_obs=self.obstacles.copy();new_fly=old_fly+self.velocity*dt;new_obs=self.positions_at(end)
        hits=[]
        for i,radius in enumerate(self.radii):
            hit,_=swept_contact(old_obs[i]-old_fly,(new_obs[i]-new_fly)-(old_obs[i]-old_fly),radius+self.c.fly_radius)
            if hit is not None:hits.append((hit,'collision',self.scenario.obstacles[i]['id']))
        bounds=np.array(self.c.bounds)+np.array([self.c.fly_radius,-self.c.fly_radius])
        for axis in range(self.c.dimensions):
            delta=new_fly[axis]-old_fly[axis]
            if delta:
                wall=bounds[axis,1] if delta>0 else bounds[axis,0];hit=(wall-old_fly[axis])/delta
                if 0<=hit<=1:hits.append((float(hit),'boundary',f'axis_{axis}'))
        contact=min(hits,key=lambda h:(h[0],h[1],h[2])) if hits else None;fraction=contact[0] if contact else 1.
        self.fly=old_fly+fraction*(new_fly-old_fly);self.obstacles=old_obs+fraction*(new_obs-old_obs);self.time_ms=start+fraction*(end-start)
        if self.first_motion_ms is None and np.any(self.fly!=old_fly):self.first_motion_ms=float(start)
        if contact:self.failure=dict(kind=contact[1],time_ms=self.time_ms,object_id=contact[2])
        else:self.velocity=advance_velocity(self.velocity,self.target,self.c.escape_acceleration_max,dt)
        return dict(start_ms=start,end_ms=self.time_ms,fly_start=old_fly,fly_end=self.fly.copy(),obstacles_start=old_obs,obstacles_end=self.obstacles.copy())

def render_camera(c,fly,obstacles,radii):
    """Stabilized camera, perspective billboards; opaque nearest-depth compositing."""
    yy,xx=np.indices((c.camera_height,c.camera_width));image=np.full(xx.shape,c.background_uint8,dtype=np.uint8)
    depth_buffer=np.full(xx.shape,np.inf);visible=0;near=0
    for ob,radius in zip(obstacles,radii):
        p=np.asarray(ob)-fly;depth=float(p[1])
        if depth<=c.camera_near_depth:near+=1;continue
        cx=c.camera_center_px[0]+c.camera_focal_px*p[0]/depth
        cy=c.camera_center_px[1]-(c.camera_focal_px*p[2]/depth if c.dimensions==3 else 0)
        rr=c.camera_focal_px*radius/depth
        mask=(xx-cx)**2+(yy-cy)**2<=rr**2
        painted=mask&(depth<depth_buffer)
        if painted.any():visible+=1
        image[painted]=c.object_uint8;depth_buffer[painted]=depth
    return image,dict(projected_objects=visible,near_or_behind=near,renderer='known_radius_billboards_not_biomechanics')
