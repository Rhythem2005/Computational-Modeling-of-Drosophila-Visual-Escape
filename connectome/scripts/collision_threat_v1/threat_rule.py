"""Approved one-candidate image geometry proxy; no fitting or world inputs."""
import math
import numpy as np
from connectome.scripts.phase8.decoder import StreamingDecoder,Threshold
from .features import FeatureExtractor

def estimate(current,previous,mode,focal_px,center_x):
    if mode not in ('expansion_only','closest_approach'):
        raise ValueError('Unregistered threat rule')
    result=dict(state='unknown',reason='|'.join(current['reasons']),
                growing=None,t_closest_s=None,d_closest_in_object_radii=None,
                point_observer_proxy=True)
    if not current['motion_valid']:
        return result
    if previous is None or not previous['measurement_valid']:
        raise ValueError('Motion marked valid without valid previous measurement')
    growing=current['radius_px']>previous['radius_px']
    result['growing']=growing
    if mode=='expansion_only':
        result.update(state='threat' if growing else 'clear_under_model',reason='expansion_only')
        return result
    def q(row):
        return np.array([(row['centroid_x_px']-center_x)/row['radius_px'],focal_px/row['radius_px']],dtype=np.float64)
    position=q(current);velocity=(position-q(previous))/current['interval_s']
    speed2=float(velocity@velocity)
    if not np.isfinite(position).all() or not np.isfinite(velocity).all() or not math.isfinite(speed2):
        raise FloatingPointError('Nonfinite geometric calculation')
    if speed2==0:
        result.update(state='clear_under_model',reason='stationary_under_model')
        return result
    t=-float(position@velocity)/speed2
    distance=float(np.linalg.norm(position+max(0.,t)*velocity))
    if not math.isfinite(t) or not math.isfinite(distance):
        raise FloatingPointError('Nonfinite closest approach')
    threat=growing and t>=0 and distance<=1
    result.update(state='threat' if threat else 'clear_under_model',reason='point_observer_closest_approach',
                  t_closest_s=t,d_closest_in_object_radii=distance)
    return result

class ThreatRule:
    def __init__(self,camera,mode):
        self.camera=camera;self.mode=mode
        if mode not in ('expansion_only','closest_approach'):raise ValueError('Unregistered mode')
        self.reset()

    def reset(self):
        self.extractor=FeatureExtractor(self.camera);self.previous=None
        self.latest=dict(state='unknown',reason='no_frame',growing=None,t_closest_s=None,
                         d_closest_in_object_radii=None,point_observer_proxy=True)
        self.latest_time=None
        self.stream=StreamingDecoder(Threshold('finite',1.),1000)

    def observe(self,frame,timestamp_s):
        measurement=self.extractor.update(frame,timestamp_s)
        self.latest=estimate(measurement,self.previous,self.mode,self.camera.focal_px,self.camera.center_x)
        self.previous=dict(measurement,reasons=list(measurement['reasons']))
        self.latest_time=float(timestamp_s)
        return dict(measurement=measurement,estimate=dict(self.latest))

    def sample(self,k):
        if self.latest_time is not None and self.latest_time>k/1000:
            raise ValueError('Future image reached threat rule')
        binary=float(self.latest['state']=='threat')
        out=self.stream.update(float(k),binary)
        out.update(score=binary,state=self.latest['state'],reason=self.latest['reason'],
                   currently_sustained_threat=bool(out['eligible'] and out['sustained_score']>=1))
        return out
