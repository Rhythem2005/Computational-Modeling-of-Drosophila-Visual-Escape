"""Same canonical solids feed room contacts, sensory rays and spectator metadata."""
import numpy as np
from ..avoidance.world import advance_velocity
from .geometry import contact_part
from .pose import unit_quaternion,heading_step

class RoomWorld:
    def __init__(self,c,scene):
        self.c=c;self.scene=scene.validate(c);self.time_ms=0.;self.fly=np.asarray(scene.fly_position,dtype=float).copy()
        self.velocity=np.asarray(scene.fly_velocity,dtype=float).copy();self.quaternion=unit_quaternion(scene.fly_quaternion)
        self.target=self.velocity.copy();self.pending=[];self.failure=None;self.first_motion_ms=None
        bounds=np.asarray(c.motion.bounds)
        if np.any(self.fly<=bounds[:,0]+c.motion.fly_radius) or np.any(self.fly>=bounds[:,1]-c.motion.fly_radius):raise ValueError('Fly starts outside room')
        for s in (*scene.static_solids,*scene.dynamic_solids):
            for part in s.parts:
                hit,_=contact_part(self.fly,np.zeros(3),s.position(0),np.zeros(3),part,c.motion.fly_radius)
                if hit is not None:raise ValueError('Initially overlapping room fixture')
    @property
    def done(self):return self.failure is not None or self.time_ms>=self.c.motion.duration_ms
    def request(self,target):
        target=np.asarray(target,dtype=float)
        if self.done or target.shape!=(3,) or not np.isfinite(target).all() or np.linalg.norm(target)>self.c.motion.escape_speed_max+1e-10:raise ValueError('Invalid room motor command')
        self.pending.append((self.time_ms+self.c.motion.actuation_delay_ms,target.copy()))
    def positions(self,t=None):return np.array([s.position(self.time_ms if t is None else t) for s in self.scene.dynamic_solids],dtype=float).reshape(-1,3)
    def step(self):
        if self.done:raise ValueError('Terminal room step')
        c=self.c.motion;start=self.time_ms;end=min(start+1,c.duration_ms);dt=(end-start)/1000
        for t,v in self.pending:
            if t<=start:self.target=v.copy()
        self.pending=[(t,v) for t,v in self.pending if t>start]
        old=self.fly.copy();q0=self.quaternion.copy();delta=self.velocity*dt;hits=[]
        for s in (*self.scene.static_solids,*self.scene.dynamic_solids):
            center=s.position(start);change=s.position(end)-center
            for j,part in enumerate(s.parts):
                hit,_=contact_part(old,delta,center,change,part,c.fly_radius)
                if hit is not None:hits.append((hit,'collision',s.id,j))
        limits=np.asarray(c.bounds)+np.array([c.fly_radius,-c.fly_radius])
        for axis in range(3):
            if delta[axis]:
                hit=(limits[axis,1 if delta[axis]>0 else 0]-old[axis])/delta[axis]
                if 0<=hit<=1:hits.append((float(hit),'boundary',f'axis_{axis}',0))
        contact=min(hits,key=lambda h:(h[0],h[1],h[2],h[3])) if hits else None;fraction=contact[0] if contact else 1.
        self.time_ms=start+(end-start)*fraction;self.fly=old+delta*fraction
        self.quaternion=heading_step(q0,self.velocity,self.c.max_heading_rate_rad_s,dt*fraction)
        if self.first_motion_ms is None and np.any(self.fly!=old):self.first_motion_ms=float(start)
        if contact:self.failure=dict(kind=contact[1],time_ms=self.time_ms,object_id=contact[2],part=contact[3])
        else:self.velocity=advance_velocity(self.velocity,self.target,c.escape_acceleration_max,dt)
        return dict(start_ms=start,end_ms=self.time_ms,fly_start=old,fly_end=self.fly.copy(),q_start=q0,q_end=self.quaternion.copy())
