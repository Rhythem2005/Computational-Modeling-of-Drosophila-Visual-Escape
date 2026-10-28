"""Ordinary locomotion and avoidance use the same delayed, bounded motor plant."""
from dataclasses import dataclass
import numpy as np
from ..avoidance.controller import Persistence
from ..avoidance.world import advance_velocity,swept_contact
from .geometry import contact_part
from .pose import rotation

@dataclass
class Command:
    target:np.ndarray|None
    mode:str
    rule:str
    initiation:bool
    unknown:bool
    feasible:bool|None
    source:str

class RoomPlanner:
    def __init__(self,c,static_prior):self.c=c;self.static_prior=tuple(static_prior)
    def evaluate(self,target,tracks,fly,velocity,active,pending,k):
        c=self.c.motion;origin=fly.copy();p=fly.copy();v=velocity.copy();target_now=active.copy();worst=float('inf')
        commands=sorted([(t,np.asarray(a)) for t,a in pending]+[(k+c.actuation_delay_ms,target)],key=lambda x:x[0]);i=0
        bounds=np.asarray(c.bounds)+np.array([c.fly_radius,-c.fly_radius])
        for step in range(c.prediction_horizon_ms):
            while i<len(commands) and commands[i][0]<=k+step:target_now=commands[i][1];i+=1
            nxt=p+v/1000;worst=min(worst,float(np.minimum(nxt-bounds[:,0],bounds[:,1]-nxt).min()))
            for solid in self.static_prior:
                for part in solid.parts:
                    _,clear=contact_part(p,nxt-p,solid.position(0),np.zeros(3),part,c.fly_radius);worst=min(worst,clear)
            for track in tracks:
                if track.relative_velocity is None:return -float('inf')
                ov=track.relative_velocity+velocity;ob=origin+track.relative_position
                start=ob+ov*step/1000-p;end=ob+ov*(step+1)/1000-nxt
                _,clear=swept_contact(start,end-start,c.object_radius_prior+c.fly_radius+getattr(track,'range_uncertainty',0.));worst=min(worst,clear)
            p=nxt;v=advance_velocity(v,target_now,c.escape_acceleration_max,.001)
        return worst
    def choose(self,tracks,fly,velocity,active,pending,k,q,desired):
        candidates=[desired.copy(),np.zeros(3),velocity.copy()]+[rotation(q)@np.asarray(d)*self.c.motion.escape_speed_max for d in self.c.motion.candidate_directions]
        choices=[];unique=[]
        for target in candidates:
            if any(np.array_equal(target,a) for a in unique):continue
            unique.append(target);clear=self.evaluate(target,tracks,fly,velocity,active,pending,k)
            choices.append((clear>self.c.motion.clearance_margin,-float(np.linalg.norm(target-desired)),clear,-len(unique),target))
        safe=[a for a in choices if a[0]]
        best=max(safe,key=lambda a:a[:4]) if safe else max(choices,key=lambda a:(a[2],a[1],a[3]))
        return best[-1],bool(best[0]),float(best[2])

class RoomBehavior:
    def __init__(self,c,model,static_prior):
        if model not in ('ordinary_motion','approach_trigger','surround_avoidance'):raise ValueError('Unreviewed controller')
        self.c=c;self.model=model;self.planner=RoomPlanner(c,static_prior);self.histories={};self.index=0;self.mode='cruise';self.last_risk=None;self.bouts=0;self.previous=None
    def update(self,k,tracks,fresh,reasons,fly,velocity,q,active,pending,new_camera):
        if k!=self.index:raise ValueError('Room decision clock must advance 1 ms')
        self.index+=1;valid=[t for t in tracks if fresh and t.motion_valid];unknown=not fresh or len(valid)!=len(tracks) or bool(reasons)
        visible_none=not tracks and reasons==['no_target_visible_not_clearance_proof']
        risks={}
        for t in valid:
            p=t.relative_position;v=t.relative_velocity;vv=float(v@v);time=float(np.clip(-(p@v)/vv,0,self.c.motion.prediction_horizon_ms/1000)) if vv else 0.
            risk=np.linalg.norm(p+v*time)<=self.c.motion.object_radius_prior+self.c.motion.fly_radius+self.c.motion.clearance_margin+getattr(t,'range_uncertainty',0)
            risks[t.identity]=bool((p@v)<0) if self.model=='approach_trigger' else bool(risk)
        ids={t.identity for t in tracks};self.histories={i:h for i,h in self.histories.items() if i in ids};confirmed=False
        for t in tracks:
            h=self.histories.setdefault(t.identity,Persistence());confirmed|=h.update(k,risks.get(t.identity,False))
        request=False;feasible=None;target=None;source='ordinary_locomotion'
        desired=rotation(q)@np.asarray(self.c.cruise_body_velocity)
        if self.model=='ordinary_motion':
            # Baseline includes exactly the same ordinary-motion command, without evasive planning.
            if new_camera:target,feasible,_=self.planner.choose([],fly,velocity,active,pending,k,q,desired)
        else:
            if confirmed:
                self.last_risk=k
                if self.mode not in ('active','infeasible'):self.bouts+=1;request=True
                self.mode='active'
            elif self.mode in ('active','infeasible'):self.mode='recovery'
            if self.mode=='recovery' and self.last_risk is not None and k-self.last_risk>=self.c.recovery_ms:
                if not unknown or (visible_none and self.c.allow_cruise_when_no_target_visible):self.mode='cruise'
            if new_camera or request:
                if unknown and not (visible_none and self.c.allow_cruise_when_no_target_visible):target=np.zeros(3);source='uncertainty_brake'
                elif self.mode in ('active','infeasible') and self.model=='approach_trigger':
                    threat=next((t for t in valid if risks.get(t.identity)),None)
                    if threat is not None:
                        away=-threat.relative_position;norm=np.linalg.norm(away);target=away/norm*self.c.motion.escape_speed_max if norm else np.zeros(3);source='simple_visual_retreat'
                else:
                    goal=np.zeros(3) if self.mode=='recovery' else desired
                    target,feasible,_=self.planner.choose(valid if self.mode!='cruise' else [],fly,velocity,active,pending,k,q,goal)
                    source='surround_visual_planner' if self.mode in ('active','recovery','infeasible') else 'ordinary_room_navigation'
                    if not feasible:self.mode='infeasible'
        if target is not None:
            if self.previous is not None and np.array_equal(target,self.previous) and not request:target=None
            else:self.previous=target.copy()
        return Command(target,self.mode,'threat' if confirmed else 'unknown' if unknown else 'clear_under_model',request,unknown,feasible,source)
