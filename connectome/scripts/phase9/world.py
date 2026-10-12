"""Deterministic piecewise-linear planar plant, swept geometry and relative camera."""
import numpy as np
from connectome.scripts.phase5.generator import render_frame
from .config import validate_config, validate_scenario


def swept_contact(p, delta, radius):
    """Entry fraction and minimum signed clearance on a relative line segment."""
    p, d = np.asarray(p,dtype=float), np.asarray(delta,dtype=float)
    if p.shape != (2,) or d.shape != (2,) or not np.all(np.isfinite(p)) or not np.all(np.isfinite(d)) or not np.isfinite(radius) or radius <= 0:
        raise ValueError("Invalid swept geometry")
    a=float(d@d); initial=float(p@p)
    if a == 0:
        return (0.0 if initial <= radius*radius else None), float(np.sqrt(initial)-radius)
    middle=-float(p@d)/a
    closest=p+np.clip(middle,0.0,1.0)*d
    clearance=float(np.linalg.norm(closest)-radius)
    if initial <= radius*radius:
        return 0.0, clearance
    perpendicular=p+middle*d
    gap=radius*radius-float(perpendicular@perpendicular)
    tolerance=64*np.finfo(float).eps*(radius*radius+float(perpendicular@perpendicular))
    if gap < -tolerance:
        return None, clearance
    entry=middle-np.sqrt(max(0.0,gap)/a)
    epsilon=64*np.finfo(float).eps
    if -epsilon <= entry <= 1+epsilon:
        return float(np.clip(entry,0.0,1.0)), clearance
    return None, clearance


def stationary_danger(config, scenario):
    """Evaluator only: future obstacle contact with a stationary initial fly."""
    c,s=validate_config(config),validate_scenario(scenario)
    horizon=c["duration_ms"]; onset=c["obstacle_motion_onset_ms"]
    first=None
    for ob in s["obstacles"]:
        p=np.asarray(ob["position"])-np.asarray(s["fly_position"])
        radius=ob["radius"]+c["fly_radius"]
        if np.linalg.norm(p) <= radius:
            return dict(danger=True, stationary_contact_ms=0.0)
        hit,_=swept_contact(p,np.asarray(ob["velocity"])*(horizon-onset)/1000,radius)
        if hit is not None:
            t=onset+hit*(horizon-onset)
            first=t if first is None else min(first,t)
    return dict(danger=first is not None, stationary_contact_ms=first)


def render_camera(config, fly, obstacles, radii):
    """Current world only; billboard approximation, using Phase 5 circle rasterizer."""
    c=config
    frame=np.full((c["camera_height"],c["camera_width"]),c["background_uint8"],dtype=np.uint8)
    projected=[]; near_or_behind=0
    for ob,radius in zip(obstacles,radii):
        relative=np.asarray(ob)-np.asarray(fly)
        depth=float(relative[1])
        if depth <= c["camera_near_depth"]:
            near_or_behind+=1; continue
        cx=c["camera_center_px"][0]+c["camera_focal_px"]*relative[0]/depth
        rr=c["camera_focal_px"]*radius/depth
        projected.append((depth,float(cx),float(rr)))
    for depth,cx,rr in sorted(projected,reverse=True):
        circle=render_frame(c["camera_width"],c["camera_height"],c["background_uint8"],c["object_uint8"],cx,c["camera_center_px"][1],rr)
        mask=circle != c["background_uint8"]; frame[mask]=circle[mask]
    return frame,dict(projected=projected,near_or_behind=near_or_behind)


class World:
    def __init__(self,config,scenario):
        self.config=validate_config(config); self.scenario=validate_scenario(scenario)
        self.fly=np.array(scenario["fly_position"],dtype=np.float64)
        self.obstacles=np.array([ob["position"] for ob in scenario["obstacles"]],dtype=np.float64)
        self.initial_obstacles=self.obstacles.copy()
        self.velocities=np.array([ob["velocity"] for ob in scenario["obstacles"]],dtype=np.float64)
        self.radii=np.array([ob["radius"] for ob in scenario["obstacles"]],dtype=np.float64)
        self.time_ms=0.0; self.speed=0.0; self.request_ms=None; self.activate_ms=None
        self.turn=0.0; self.direction=np.array([0.,-1.]); self.first_motion_ms=None
        self.path_length=0.0; self.terminated=False; self.truncated=False; self.failure=None
        self.min_clearance=self.clearance()
        bounds=np.array(self.config["bounds_xy"]); allowed=bounds+np.array([self.config["fly_radius"],-self.config["fly_radius"]])
        if self.min_clearance <= 0:
            self.terminated=True; self.failure=dict(kind="collision",time_ms=0.0)
        elif np.any(self.fly <= allowed[:,0]) or np.any(self.fly >= allowed[:,1]):
            self.terminated=True; self.failure=dict(kind="boundary",time_ms=0.0)

    @property
    def done(self):
        return self.terminated or self.truncated

    def clearance(self):
        return float(np.min(np.linalg.norm(self.obstacles-self.fly,axis=1)-self.radii-self.config["fly_radius"]))

    def request(self,turn):
        if self.done:
            raise ValueError("Cannot issue action after world termination")
        if isinstance(turn,bool) or not np.isfinite(turn) or not -1 <= turn <= 1:
            raise ValueError("Turn must be finite and within [-1,1]")
        if self.request_ms is not None:
            return False
        self.request_ms=self.time_ms; self.activate_ms=self.time_ms+self.config["actuation_delay_ms"]
        self.turn=float(turn)
        theta=np.deg2rad(turn*self.config["escape_lateral_angle_max_deg"])
        self.direction=np.array([np.sin(theta),-np.cos(theta)])
        return True

    def step(self):
        if self.done:
            raise ValueError("World step after episode end")
        c=self.config; start=self.time_ms
        end=min(start+1.0,float(c["duration_ms"])); dt=(end-start)/1000
        old_fly=self.fly.copy(); old_obstacles=self.obstacles.copy()
        active=self.activate_ms is not None and start >= self.activate_ms
        displacement=self.direction*self.speed*dt if active else np.zeros(2)
        new_fly=old_fly+displacement
        elapsed=max(0.0,end-c["obstacle_motion_onset_ms"])/1000
        new_obstacles=self.initial_obstacles+self.velocities*elapsed
        contacts=[]
        for index,(old,new,radius) in enumerate(zip(old_obstacles,new_obstacles,self.radii)):
            p=old-old_fly; d=(new-new_fly)-p
            hit,_=swept_contact(p,d,radius+c["fly_radius"])
            if hit is not None:
                contacts.append((hit,0,self.scenario["obstacles"][index]["id"],"collision"))
        bounds=np.array(c["bounds_xy"])+np.array([c["fly_radius"],-c["fly_radius"]])
        for axis in (0,1):
            delta=new_fly[axis]-old_fly[axis]
            if delta != 0:
                wall=bounds[axis,1] if delta > 0 else bounds[axis,0]
                hit=(wall-old_fly[axis])/delta
                if 0 <= hit <= 1:
                    contacts.append((float(hit),1,f"axis_{axis}","boundary"))
        contact=min(contacts) if contacts else None
        fraction=1.0 if contact is None else contact[0]
        self.fly=old_fly+fraction*(new_fly-old_fly)
        self.obstacles=old_obstacles+fraction*(new_obstacles-old_obstacles)
        self.time_ms=start+fraction*(end-start)
        for old,new,radius in zip(old_obstacles,self.obstacles,self.radii):
            _,clearance=swept_contact(old-old_fly,(new-self.fly)-(old-old_fly),radius+c["fly_radius"])
            self.min_clearance=min(self.min_clearance,clearance)
        distance=float(np.linalg.norm(self.fly-old_fly)); self.path_length+=distance
        if distance > 0 and self.first_motion_ms is None:
            self.first_motion_ms=start
        if active:
            self.speed=min(c["escape_speed_max"],self.speed+c["escape_acceleration_max"]*(self.time_ms-start)/1000)
        if contact:
            self.terminated=True; self.failure=dict(kind=contact[3],time_ms=self.time_ms,object_id=contact[2])
        elif self.time_ms == c["duration_ms"]:
            self.truncated=True
        return dict(start_ms=start,end_ms=self.time_ms,fly_start=old_fly,fly_end=self.fly.copy(),
                    obstacles_start=old_obstacles,obstacles_end=self.obstacles.copy())

    def metrics(self):
        if not self.done:
            raise ValueError("Metrics require a completed episode")
        danger=stationary_danger(self.config,self.scenario)
        timely=self.request_ms is not None and (danger["stationary_contact_ms"] is None or self.request_ms < danger["stationary_contact_ms"])
        success=None if not danger["danger"] else bool(timely and self.truncated and self.clearance() >= self.config["success_final_clearance_min"])
        early=self.request_ms is not None and self.request_ms < self.config["obstacle_motion_onset_ms"]
        latency=None if self.request_ms is None or early else self.request_ms-self.config["obstacle_motion_onset_ms"]
        return dict(**danger,first_request_ms=self.request_ms,pre_onset_request=early,onset_relative_latency_ms=latency,
                    scheduled_actuation_ms=self.activate_ms,first_motion_ms=self.first_motion_ms,turn=self.turn,
                    terminated=self.terminated,truncated=self.truncated,failure=self.failure,end_ms=self.time_ms,
                    survived_horizon=self.truncated and not self.terminated,escape_success=success,
                    dangerous_miss=bool(danger["danger"] and not timely),false_alarm=bool(not danger["danger"] and self.request_ms is not None),
                    minimum_swept_clearance=self.min_clearance,final_clearance=self.clearance(),path_length=self.path_length,
                    interpretation="finite-horizon engineering fixture; no calibrated fly behavior or architecture advantage")
