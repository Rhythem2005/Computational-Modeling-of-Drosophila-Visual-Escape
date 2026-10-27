"""Pixels and timestamps only: no simulator IDs, future paths or object coordinates."""
from collections import deque
from dataclasses import dataclass
import math
import numpy as np

@dataclass
class Detection:
    centroid:np.ndarray
    radius_px:float
    relative_position:np.ndarray
    valid:bool
    reasons:list

@dataclass
class Track:
    identity:int
    time_ms:float
    centroid:np.ndarray
    radius_px:float
    relative_position:np.ndarray
    relative_velocity:np.ndarray|None
    motion_valid:bool
    reasons:list

def components(mask):
    """Eight-connected labels without a new runtime dependency."""
    seen=np.zeros(mask.shape,dtype=bool);h,w=mask.shape
    for y,x in zip(*np.nonzero(mask)):
        if seen[y,x]:continue
        todo=[(int(y),int(x))];seen[y,x]=True;points=[]
        while todo:
            yy,xx=todo.pop();points.append((yy,xx))
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    yn,xn=yy+dy,xx+dx
                    if 0<=yn<h and 0<=xn<w and mask[yn,xn] and not seen[yn,xn]:seen[yn,xn]=True;todo.append((yn,xn))
        yield np.asarray(points)

class VisualTracker:
    def __init__(self,c):self.c=c;self.reset()
    def reset(self):self.tracks=[];self.next_id=0;self.time_ms=None
    def observe(self,image,time_ms):
        c=self.c
        if image.dtype!=np.uint8 or image.shape!=(c.camera_height,c.camera_width):raise ValueError('Camera schema mismatch')
        if not math.isfinite(time_ms) or time_ms<0 or (self.time_ms is not None and time_ms<=self.time_ms):raise ValueError('Noncausal camera timestamps')
        mask=np.abs(image.astype(np.int16)-c.background_uint8)>=c.min_contrast_uint8
        detections=[];global_reasons=[]
        if not mask.any():global_reasons.append('no_visible_object_depth_unknown')
        if mask.sum()>=image.size/2:global_reasons.append('foreground_dominant')
        for points in components(mask):
            if len(detections)>=64:global_reasons.append('component_capacity_exceeded');break
            yy,xx=points.T;cx=float(xx.mean());cy=float(yy.mean());rr=math.sqrt(len(points)/math.pi)
            reasons=[]
            if (yy==0).any() or (xx==0).any() or (yy==c.camera_height-1).any() or (xx==c.camera_width-1).any():reasons.append('border_contact')
            # Raster circle mismatch also catches many merged/partially occluded silhouettes.
            gy,gx=np.indices(image.shape);ideal=(gx-cx)**2+(gy-cy)**2<=rr**2
            observed=np.zeros(image.shape,dtype=bool);observed[yy,xx]=True
            if np.count_nonzero(ideal^observed)/len(points)>c.max_shape_error_fraction:reasons.append('noncircular_or_occluded')
            depth=c.camera_focal_px*c.object_radius_prior/rr
            p=np.array([(cx-c.camera_center_px[0])*depth/c.camera_focal_px,depth]+([(c.camera_center_px[1]-cy)*depth/c.camera_focal_px] if c.dimensions==3 else []))
            detections.append(Detection(np.array([cx,cy]),rr,p,not reasons,reasons))
        old=self.tracks;fresh=[];dt=None if self.time_ms is None else (time_ms-self.time_ms)/1000
        adjacent=dt is not None and abs(dt-1/c.camera_fps)<=64*np.finfo(float).eps*max(1,time_ms/1000)
        distances=np.array([[np.linalg.norm(t.centroid-d.centroid) for d in detections] for t in old]).reshape(len(old),len(detections))
        candidates={j:[] for j in range(len(detections))}
        for i in range(len(old)):
            for j in range(len(detections)):
                if distances[i,j]<=c.association_gate_px:candidates[j].append(i)
        assigned=set()
        for j,d in enumerate(detections):
            reasons=list(d.reasons);possible=candidates[j];match=None
            if possible:
                ranked=sorted(possible,key=lambda i:(distances[i,j],old[i].identity));i=ranked[0]
                competing=[jj for jj in range(len(detections)) if distances[i,jj]<=c.association_gate_px]
                ambiguous=(len(ranked)>1 and distances[ranked[1],j]-distances[i,j]<=c.association_ambiguity_px)
                ambiguous|=len(competing)>1 and sorted(distances[i,jj] for jj in competing)[1]-distances[i,j]<=c.association_ambiguity_px
                # A merged blob may sit between two previous tracks. Never assert a clean identity.
                ambiguous|=len(detections)<len(old) and len(possible)>1
                if ambiguous:reasons.append('association_ambiguous')
                elif i not in assigned:match=old[i];assigned.add(i)
            if match is None:
                identity=self.next_id;self.next_id+=1;velocity=None;motion=False;reasons.append('insufficient_track_history')
            else:
                identity=match.identity
                if not adjacent:reasons.append('timestamp_gap')
                if abs(d.radius_px-match.radius_px)/match.radius_px>c.max_radius_fraction_change:reasons.append('radius_change_outside_contract')
                # A new track's first valid observation can establish the next derivative.
                prior_valid=not any(r not in ('insufficient_track_history',) for r in match.reasons)
                motion=d.valid and prior_valid and adjacent and not reasons
                velocity=(d.relative_position-match.relative_position)/dt if motion else None
            fresh.append(Track(identity,time_ms,d.centroid,d.radius_px,d.relative_position,velocity,bool(motion),reasons))
        if len(assigned)<len(old):global_reasons.append('lost_or_merged_track')
        self.tracks=fresh;self.time_ms=time_ms
        return fresh,global_reasons

    def current(self,time_ms):
        if self.time_ms is None or time_ms<self.time_ms:raise ValueError('Observation not yet available')
        fresh=time_ms-self.time_ms<=self.c.max_observation_age_ms
        return self.tracks,fresh
