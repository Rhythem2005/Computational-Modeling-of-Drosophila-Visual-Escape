"""Right-handed x-right, y-forward, z-up; quaternions are (x,y,z,w)."""
import math
import numpy as np

def unit_quaternion(q):
    q=np.asarray(q,dtype=np.float64)
    if q.shape!=(4,) or not np.isfinite(q).all() or not np.isclose(q@q,1.,atol=1e-10):raise ValueError('Normalized finite XYZW quaternion required')
    return q.copy()/np.linalg.norm(q)

def multiply(a,b):
    a=unit_quaternion(a);b=unit_quaternion(b);x,y,z,w=a;u,v,s,t=b
    return unit_quaternion([w*u+x*t+y*s-z*v,w*v-x*s+y*t+z*u,w*s+x*v-y*u+z*t,w*t-x*u-y*v-z*s])

def rotation(q):
    x,y,z,w=unit_quaternion(q)
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
      [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
      [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])

def axis_angle(axis,angle):
    axis=np.asarray(axis,dtype=float);norm=np.linalg.norm(axis)
    if norm==0 or not math.isfinite(angle):raise ValueError('Invalid rotation axis/angle')
    return np.r_[axis/norm*math.sin(angle/2),math.cos(angle/2)]

def slerp(a,b,t):
    if not 0<=t<=1:raise ValueError('Interpolation outside segment')
    a=unit_quaternion(a);b=unit_quaternion(b);dot=float(a@b)
    if dot<0:b=-b;dot=-dot
    dot=np.clip(dot,-1,1)
    if dot>.9995:
        q=a+(b-a)*t;return q/np.linalg.norm(q)
    theta=math.acos(dot)
    return (math.sin((1-t)*theta)*a+math.sin(t*theta)*b)/math.sin(theta)

def heading_step(q,velocity,max_rate,dt):
    """Yaw-only kinematic heading; no implicit aerodynamic bank or gravity."""
    forward=rotation(q)[:,1];v=np.asarray(velocity)
    if np.linalg.norm(v[:2])==0 or np.linalg.norm(forward[:2])==0:return unit_quaternion(q)
    angle=math.atan2(forward[0]*v[1]-forward[1]*v[0],float(forward[:2]@v[:2]))
    return multiply(axis_angle([0,0,1],float(np.clip(angle,-max_rate*dt,max_rate*dt))),q)
