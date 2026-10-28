"""Declared color/size-prior observer; seam association and ego-motion compensation."""
from dataclasses import dataclass
import math
import numpy as np
from ..avoidance.perception import components,Track
from .pose import rotation
from .sensors import pixel_rays

@dataclass
class Candidate:
    relative:np.ndarray
    low:float
    high:float
    bearing:np.ndarray
    view:str
    pixel_count:int
    valid:bool
    reasons:list

class SurroundObserver:
    def __init__(self,c):self.c=c;self.reset()
    def reset(self):self.previous=[];self.next_id=0;self.time=None;self.last_reasons=['no_observation']
    def observe(self,observation):
        c=self.c;settings=c.vision;now=observation.time_ms
        if [(v.id,v.quaternion,v.width,v.height,v.focal_px) for v in observation.views]!=[(v.id,v.quaternion,v.width,v.height,v.focal_px) for v in c.views] or len(observation.images)!=len(c.views):raise ValueError('Surround calibration differs')
        if any(image.dtype!=np.uint8 or image.shape!=(v.height,v.width,3) for image,v in zip(observation.images,c.views)):raise ValueError('Expected calibrated RGB sensor images')
        if self.time is not None and now<=self.time:raise ValueError('Noncausal surround image clock')
        candidates=[];reasons=[]
        for view,image in zip(observation.views,observation.images):
            mask=np.linalg.norm(image.astype(float)-np.asarray(settings.target_rgb),axis=-1)<=settings.color_distance
            rays=pixel_rays(view)@rotation(view.quaternion).T@rotation(observation.quaternion).T
            for points in components(mask):
                if len(points)<settings.min_component_pixels:continue
                yy,xx=points.T;rr=rays[yy,xx];bearing=rr.mean(axis=0);bearing/=np.linalg.norm(bearing)
                angles=np.arccos(np.clip(rr@bearing,-1,1));alpha=float(angles.max());error=math.atan(settings.range_pixel_uncertainty/view.focal_px)
                local=[]
                border=bool((yy==0).any() or (xx==0).any() or (yy==view.height-1).any() or (xx==view.width-1).any())
                if border:local.append('view_border_partial')
                if alpha<=error or alpha+error>=math.pi/2:local.append('size_unresolved')
                # Boundary rays should lie on a circular angular silhouette for a sphere.
                pointset=set(map(tuple,points.tolist()));boundary=[(y,x) for y,x in pointset if any((y+dy,x+dx) not in pointset for dy,dx in ((1,0),(-1,0),(0,1),(0,-1)))]
                ba=np.arccos(np.clip(np.array([rays[y,x] for y,x in boundary])@bearing,-1,1))
                if len(ba) and float(np.ptp(ba))>settings.max_cone_error_rad:local.append('unsupported_silhouette_or_merge')
                effective=max(alpha,error);distance=c.motion.object_radius_prior/math.sin(effective)
                lo=c.motion.object_radius_prior/math.sin(min(math.pi/2,effective+error));hi=c.motion.object_radius_prior/math.sin(max(effective-error,1e-12))
                candidates.append(Candidate(bearing*distance,lo,hi,bearing,view.id,len(points),not local,local))
        # Fuse observations of one silhouette across different views only. Ambiguous
        # groups containing two detections in one view are never assigned one identity.
        groups=[]
        for candidate in sorted(candidates,key=lambda x:(-x.pixel_count,x.view)):
            matches=[]
            for i,g in enumerate(groups):
                best=g[0];angle=math.acos(float(np.clip(best.bearing@candidate.bearing,-1,1)))
                if angle<=settings.seam_merge_angle_rad and max(best.low,candidate.low)<=min(best.high,candidate.high):matches.append(i)
            if len(matches)==1:
                g=groups[matches[0]]
                if any('ambiguous_seam_or_overlap' in v.reasons for v in g):candidate.valid=False;candidate.reasons.append('ambiguous_seam_or_overlap')
                if any(v.view==candidate.view for v in g):
                    for v in g:v.valid=False;v.reasons.append('ambiguous_seam_or_overlap')
                    candidate.valid=False;candidate.reasons.append('ambiguous_seam_or_overlap')
                g.append(candidate)
            elif matches:
                candidate.valid=False;candidate.reasons.append('ambiguous_seam_group');groups.append([candidate])
            else:groups.append([candidate])
        detections=[next((x for x in g if x.valid),g[0]) for g in groups]
        if len(detections)>64:detections=detections[:64];reasons.append('track_capacity_exceeded')
        old=self.previous;fresh=[];assigned=set();dt=None if self.time is None else (now-self.time)/1000
        for det in detections:
            wp=observation.position+det.relative;possible=sorted([(float(np.linalg.norm(wp-o['position'])),i) for i,o in enumerate(old) if i not in assigned])
            usable=[(d,i) for d,i in possible if d<=settings.association_distance];prior=None;local=list(det.reasons)
            if len(usable)>1 and usable[1][0]-usable[0][0]<=settings.association_ambiguity:local.append('identity_ambiguous')
            elif usable:prior=old[usable[0][1]];assigned.add(usable[0][1])
            if prior is None:identity=self.next_id;self.next_id+=1;velocity=None;local.append('insufficient_history')
            else:
                identity=prior['id'];adjacent=0<now-prior['time']<=settings.max_gap_ms
                if not adjacent:local.append('observation_gap')
                velocity=(wp-prior['position'])/dt if adjacent and prior['valid'] and det.valid and not local else None
            valid=det.valid and velocity is not None and not local
            fresh.append(dict(id=identity,position=wp.copy(),relative=det.relative.copy(),velocity=velocity,time=now,valid=det.valid and not any(r!='insufficient_history' for r in local),motion_valid=valid,reasons=local,range_interval=[det.low,det.high],views=[x.view for g in groups if any(v is det for v in g) for x in g]))
        if len(assigned)<len(old):reasons.append('lost_track_or_occlusion')
        # No visible target is not certified empty space: coverage, material and
        # occlusion assumptions remain explicit even when normal cruise is allowed.
        if not detections:reasons.append('no_target_visible_not_clearance_proof')
        self.previous=fresh;self.time=now;self.last_reasons=reasons
        return fresh,reasons
    def tracks(self,time_ms,position,velocity):
        if self.time is None or time_ms<self.time:raise ValueError('Future observation queried')
        fresh=time_ms-self.time<=self.c.motion.max_observation_age_ms
        rows=[]
        for x in self.previous:
            age=(time_ms-x['time'])/1000
            rel=x['position']+(x['velocity']*age if x['velocity'] is not None else 0)-position
            v=None if x['velocity'] is None else x['velocity']-velocity
            track=Track(x['id'],time_ms,np.zeros(2),0.,rel,v,x['motion_valid'] and fresh,list(x['reasons']))
            center=float(np.linalg.norm(x['relative']));track.range_uncertainty=max(abs(x['range_interval'][0]-center),abs(x['range_interval'][1]-center))
            rows.append(track)
        return rows,fresh
