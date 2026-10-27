"""Inspectable dynamics-aware trajectory search; controller inputs are estimates."""
from dataclasses import dataclass
import numpy as np
from .world import advance_velocity,swept_contact

@dataclass
class Plan:
    target:np.ndarray
    feasible:bool
    clearance:float
    reason:str

class LocalPlanner:
    def __init__(self,c):self.c=c
    def choose(self,tracks,fly,velocity,active_target,pending,time_ms,previous):
        c=self.c
        candidates=[np.zeros(c.dimensions),velocity.copy(),previous.copy()]
        candidates +=[np.asarray(d,dtype=float)*c.escape_speed_max for d in c.candidate_directions]
        unique=[]
        for v in candidates:
            if not any(np.array_equal(v,u) for u in unique):unique.append(v)
        evaluations=[]
        for order,target in enumerate(unique):
            clear=self.evaluate(target,tracks,fly,velocity,active_target,pending,time_ms)
            # Prefer safe clearance, then small command changes; no fitted score weights.
            evaluations.append((clear>c.clearance_margin,clear,-float(np.linalg.norm(target-previous)),-order,target))
        best=max(evaluations,key=lambda v:v[:4])
        return Plan(best[4],bool(best[0]),float(best[1]),'predicted_feasible' if best[0] else 'no_predicted_feasible_candidate')

    def evaluate(self,target,tracks,fly,velocity,active_target,pending,time_ms):
        c=self.c;origin=fly.copy();p=fly.copy();v=velocity.copy();current=active_target.copy();worst=float('inf')
        commands=[(float(t),np.asarray(a).copy()) for t,a in pending]+[(time_ms+c.actuation_delay_ms,target)]
        commands.sort(key=lambda x:x[0]);next_command=0
        bounds=np.array(c.bounds)+np.array([c.fly_radius,-c.fly_radius])
        # Match the actual 1 ms plant, including queued commands.
        for k in range(c.prediction_horizon_ms):
            now=time_ms+k
            while next_command<len(commands) and commands[next_command][0]<=now:
                current=commands[next_command][1];next_command+=1
            nxt=p+v/1000
            worst=min(worst,float(np.min(np.minimum(nxt-bounds[:,0],bounds[:,1]-nxt))))
            for track in tracks:
                if track.relative_velocity is None:return -float('inf')
                age=(time_ms-track.time_ms)/1000
                ob0=origin+track.relative_position+track.relative_velocity*age
                # Convert observed relative motion using current proprioceptive velocity.
                ov=track.relative_velocity+velocity
                start=ob0+ov*k/1000-p;end=ob0+ov*(k+1)/1000-nxt
                hit,clear=swept_contact(start,end-start,c.object_radius_prior+c.fly_radius)
                worst=min(worst,clear)
                if hit is not None:worst=min(worst,0.)
            p=nxt;v=advance_velocity(v,current,c.escape_acceleration_max,.001)
        return worst
