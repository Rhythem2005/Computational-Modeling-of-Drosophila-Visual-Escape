"""Repeated avoidance policy, separately attributed from the fixed anatomical circuit."""
from collections import deque
from dataclasses import dataclass
import numpy as np
from .planning import LocalPlanner,Plan

class Persistence:
    """Unchanged elapsed-time convention: closed [k-20,k], not 20 samples."""
    def __init__(self):self.values=deque();self.last=None
    def update(self,k,value):
        if self.last is not None and k!=self.last+1:raise ValueError('Persistence requires consecutive ticks')
        self.last=k;self.values.append((k,bool(value)))
        while self.values and self.values[0][0]<k-20:self.values.popleft()
        return len(self.values)==21 and all(v for _,v in self.values)

@dataclass
class Decision:
    target:np.ndarray|None
    phase:str
    rule:str
    request:bool
    feasible:bool|None
    unknown:bool
    track_count:int

class AvoidanceController:
    def __init__(self,c,model):
        self.c=c;self.model=model;self.planner=LocalPlanner(c);self.histories={};self.clear=Persistence()
        self.phase='observing';self.previous=np.zeros(c.dimensions);self.armed=False;self.index=0;self.bouts=0;self.legacy_used=False
    def update(self,k,tracks,fresh,perception_reasons,circuit_requested,fly,velocity,active_target,pending,new_camera):
        if k!=self.index:raise ValueError('Noncausal controller clock')
        self.index+=1;self.armed|=bool(circuit_requested)
        valid=bool(tracks) and fresh and not perception_reasons and all(t.motion_valid for t in tracks)
        risks={}
        if valid:
            for t in tracks:
                p=t.relative_position+t.relative_velocity*(k-t.time_ms)/1000
                horizon=self.c.prediction_horizon_ms/1000;v=t.relative_velocity;vv=float(v@v)
                closest=float(np.clip(-(p@v)/vv,0,horizon)) if vv else 0.
                risks[t.identity]=bool(np.linalg.norm(p+v*closest)<=self.c.object_radius_prior+self.c.fly_radius+self.c.clearance_margin)
        threats=[]
        identities={t.identity for t in tracks}
        for ident in list(self.histories):
            if ident not in identities:del self.histories[ident]
        for t in tracks:
            if t.identity not in self.histories:self.histories[t.identity]=Persistence()
            if self.histories[t.identity].update(k,valid and (float(t.relative_position@t.relative_velocity)<0 if self.model=='simple_trigger' else risks.get(t.identity,False))):threats.append(t.identity)
        clear_now=self.clear.update(k,valid and not any(risks.values()))
        unknown=not valid;target=None;request=False;feasible=None
        if self.model=='no_action':return Decision(None,'observing','unknown' if unknown else 'threat' if any(risks.values()) else 'clear_under_model',False,None,unknown,len(tracks))
        if self.model in ('simple_trigger','frozen_latched'):
            trigger=bool(threats) if self.model=='simple_trigger' else self.armed
            if trigger and not self.legacy_used:
                target=np.zeros(self.c.dimensions);target[1]=-self.c.escape_speed_max
                self.legacy_used=True;self.phase='active';request=True;self.bouts=1
        else:
            permission=self.model=='planner_only' or self.armed
            if threats and permission and self.phase in ('observing','recovering'):self.phase='active';self.bouts+=1;request=True
            if self.phase=='active' and clear_now:self.phase='recovering'
            if self.phase=='recovering' and clear_now and np.linalg.norm(velocity)==0 and not np.any(active_target) and all(not np.any(v) for _,v in pending):self.phase='observing'
            if self.phase=='active' and (new_camera or request):
                if valid:
                    plan=self.planner.choose(tracks,fly,velocity,active_target,pending,k,self.previous);target=plan.target;feasible=plan.feasible
                    if not feasible:self.phase='infeasible'
                else:
                    # Unknown is not safe. Brake and report unsupported perception, not a certified escape.
                    target=np.zeros(self.c.dimensions)
            elif self.phase in ('recovering','infeasible') and new_camera:
                target=np.zeros(self.c.dimensions)
                if self.phase=='recovering' and valid:
                    braking=self.planner.evaluate(target,tracks,fly,velocity,active_target,pending,k)
                    if braking<=self.c.clearance_margin:
                        plan=self.planner.choose(tracks,fly,velocity,active_target,pending,k,self.previous)
                        target=plan.target;feasible=plan.feasible;self.phase='active' if feasible else 'infeasible'
            if self.phase=='infeasible' and threats and permission and new_camera:
                plan=self.planner.choose(tracks,fly,velocity,active_target,pending,k,self.previous) if valid else None
                if plan is not None and plan.feasible:self.phase='active';target=plan.target;feasible=True
        if target is not None:
            if np.array_equal(target,self.previous) and not request:target=None
            else:self.previous=target.copy()
        return Decision(target,self.phase,'unknown' if unknown else 'threat' if any(risks.values()) else 'clear_under_model',request,feasible,unknown,len(tracks))
