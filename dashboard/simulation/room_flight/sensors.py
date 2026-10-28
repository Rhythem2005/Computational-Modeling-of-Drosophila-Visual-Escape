"""Calibrated RGB-only surround rendering; no depth or evaluator IDs in observations."""
from dataclasses import dataclass
import math
import numpy as np
from .contracts import View
from .pose import axis_angle,rotation,unit_quaternion
from .geometry import ray_part

@dataclass(frozen=True)
class Observation:
    time_ms:float
    position:np.ndarray
    quaternion:np.ndarray
    images:tuple
    views:tuple

def axis_rig(width,height,focal_px):
    """Engineering full-coverage candidate, not an anatomical compound-eye claim."""
    rotations=[('front',[0,0,1],0),('rear',[0,0,1],math.pi),('left',[0,0,1],math.pi/2),('right',[0,0,1],-math.pi/2),('above',[1,0,0],math.pi/2),('below',[1,0,0],-math.pi/2)]
    return tuple(View(name,tuple(axis_angle(axis,a)),width,height,focal_px) for name,axis,a in rotations)

def pixel_rays(view):
    yy,xx=np.indices((view.height,view.width));rays=np.stack(((xx+.5-view.width/2)/view.focal_px,np.ones_like(xx),(view.height/2-yy-.5)/view.focal_px),axis=-1)
    return rays/np.linalg.norm(rays,axis=-1,keepdims=True)

class SurroundRenderer:
    def __init__(self,c):self.c=c;self.rays=tuple(pixel_rays(v) for v in c.views)
    def capture(self,scene,position,quaternion,time_ms):
        position=np.asarray(position,dtype=float);q=unit_quaternion(quaternion);body=rotation(q);images=[]
        bounds=np.asarray(self.c.motion.bounds)
        if np.any(position<=bounds[:,0]) or np.any(position>=bounds[:,1]):raise ValueError('Camera outside room')
        for view,rays in zip(self.c.views,self.rays):
            world_rays=rays@rotation(view.quaternion).T@body.T
            # From an interior origin the nearest outgoing box plane is a room surface.
            limits=np.where(world_rays>=0,bounds[:,1],bounds[:,0])
            distance=np.divide(limits-position,world_rays,out=np.full_like(world_rays,np.inf),where=np.abs(world_rays)>1e-15).min(axis=-1)
            image=np.empty((*distance.shape,3),dtype=np.uint8);image[:]=self.c.room_color
            for solid in (*scene.static_solids,*scene.dynamic_solids):
                center=solid.position(time_ms)
                for part in solid.parts:
                    candidate=ray_part(position,world_rays,center,part)
                    mask=(candidate>=self.c.motion.camera_near_depth)&(candidate<distance)
                    image[mask]=part.color;distance[mask]=candidate[mask]
            image.flags.writeable=False;images.append(image)
        # No distance, material/object IDs or scene handle survives this boundary.
        pos=position.copy();pos.flags.writeable=False;q.flags.writeable=False
        return Observation(float(time_ms),pos,q,tuple(images),self.c.views)

def mosaic(observation):
    h,w=observation.images[0].shape[:2];result=np.zeros((h*2,w*3,3),dtype=np.uint8)
    for i,image in enumerate(observation.images):result[(i//3)*h:(i//3+1)*h,(i%3)*w:(i%3+1)*w]=image
    return result
