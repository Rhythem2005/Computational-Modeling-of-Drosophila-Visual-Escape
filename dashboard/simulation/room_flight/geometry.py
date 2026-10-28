"""Canonical rigid solids used for both ray sensing and swept finite-body contact."""
from dataclasses import dataclass,asdict
import math
import numpy as np
from ..avoidance.world import swept_contact
from .pose import unit_quaternion,rotation

@dataclass(frozen=True)
class Part:
    shape:str
    offset:tuple
    quaternion:tuple
    color:tuple
    radius:float|None=None
    half_extents:tuple|None=None
    def __post_init__(self):
        p=np.asarray(self.offset,dtype=float)
        if p.shape!=(3,) or not np.isfinite(p).all():raise ValueError('Invalid solid offset')
        unit_quaternion(self.quaternion)
        if len(self.color)!=3 or any(type(v) is not int or not 0<=v<=255 for v in self.color):raise ValueError('RGB material required')
        if self.shape=='sphere':
            if self.radius is None or not math.isfinite(self.radius) or self.radius<=0 or self.half_extents is not None:raise ValueError('Invalid sphere')
        elif self.shape=='box':
            h=np.asarray(self.half_extents,dtype=float)
            if h.shape!=(3,) or not np.isfinite(h).all() or np.any(h<=0) or self.radius is not None:raise ValueError('Invalid box')
        else:raise ValueError('Only exact sphere/box/compound-of-parts geometry supported')
    def public(self):return asdict(self)

def ray_part(origin,rays,center,part):
    """Nearest nonnegative ray distance. No object identity is returned to sensors."""
    R=rotation(part.quaternion);o=(origin-center-np.asarray(part.offset))@R;d=rays@R
    if part.shape=='sphere':
        b=np.sum(d*o,axis=-1);cc=float(o@o)-part.radius**2;disc=b*b-cc
        root=np.sqrt(np.maximum(0,disc));a=-b-root;b2=-b+root
        return np.where((disc>=0)&(b2>=0),np.where(a>=0,a,b2),np.inf)
    h=np.asarray(part.half_extents);parallel=np.abs(d)<1e-15
    inv=np.divide(1.,d,out=np.zeros_like(d),where=~parallel)
    t1=(-h-o)*inv;t2=(h-o)*inv
    lo=np.where(parallel,-np.inf,np.minimum(t1,t2));hi=np.where(parallel,np.inf,np.maximum(t1,t2))
    enter=lo.max(axis=-1);leave=hi.min(axis=-1)
    valid=~np.any(parallel&(np.abs(o)>h),axis=-1)&(leave>=np.maximum(enter,0))
    return np.where(valid,np.where(enter>=0,enter,leave),np.inf)

def swept_sphere_box(p,d,h,radius):
    """Exact translating sphere/box contact including rounded edges/corners."""
    p=np.asarray(p,dtype=float);d=np.asarray(d,dtype=float);h=np.asarray(h,dtype=float)
    breaks=[0.,1.]
    for j in range(3):
        if d[j]:
            for edge in (-h[j],h[j]):
                t=(edge-p[j])/d[j]
                if 0<t<1:breaks.append(float(t))
    breaks=sorted(set(breaks));earliest=None;minimum=float('inf')
    for lo,hi in zip(breaks[:-1],breaks[1:]):
        mid=p+d*((lo+hi)/2);active=np.abs(mid)>h
        a=np.where(active,p-np.sign(mid)*h,0);b=np.where(active,d,0)
        aa=float(b@b);bb=float(2*a@b);cc=float(a@a)-radius**2
        t=lo if aa==0 else float(np.clip(-bb/(2*aa),lo,hi))
        minimum=min(minimum,float(np.linalg.norm(a+b*t)-radius))
        f=aa*lo*lo+bb*lo+cc
        if f<=0:hit=lo
        elif aa:
            disc=bb*bb-4*aa*cc;tol=64*np.finfo(float).eps*(bb*bb+abs(4*aa*cc)+1)
            hit=(-bb-math.sqrt(max(0,disc)))/(2*aa) if disc>=-tol else None
            if hit is not None and not lo-1e-12<=hit<=hi+1e-12:hit=None
        else:hit=None
        if hit is not None:earliest=float(np.clip(hit,0,1)) if earliest is None else min(earliest,float(np.clip(hit,0,1)))
    return earliest,minimum

def contact_part(start,delta,center,center_delta,part,fly_radius):
    R=rotation(part.quaternion);p=(start-center-np.asarray(part.offset))@R;d=(delta-center_delta)@R
    return swept_contact(p,d,part.radius+fly_radius) if part.shape=='sphere' else swept_sphere_box(p,d,np.asarray(part.half_extents),fly_radius)
