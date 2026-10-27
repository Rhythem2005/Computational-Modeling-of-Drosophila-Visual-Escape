"""Only contact-radius inflation changes; v1 observation/arithmetic is reused."""
from dataclasses import dataclass
from numbers import Real
import math
from connectome.scripts.collision_threat_v1.threat_rule import ThreatRule,estimate

@dataclass(frozen=True)
class KnownSizePrior:
    object_radius: float
    self_radius: float

    def __post_init__(self):
        values=(self.object_radius,self.self_radius)
        if (any(isinstance(x,bool) or not isinstance(x,Real) or not math.isfinite(x) or x<=0 for x in values)
                or values!=(1.5,.5)):
            raise ValueError('Only the approved fixed 1.5 object / 0.5 self-radius prior is supported')

    @property
    def contact_radius(self):return 1+self.self_radius/self.object_radius

def inflate(point_estimate,prior):
    if not isinstance(prior,KnownSizePrior):raise ValueError('Explicit approved known-size prior required')
    out=dict(point_estimate,point_observer_proxy=False,known_size_prior=True,
             normalized_contact_radius=prior.contact_radius)
    if out['state']=='unknown' or out['reason']=='stationary_under_model':return out
    d=out['d_closest_in_object_radii'];t=out['t_closest_s']
    if d is None or t is None or not math.isfinite(d) or not math.isfinite(t):
        raise FloatingPointError('Undefined/nonfinite finite-body estimate')
    threat=out['growing'] and t>=0 and d<=prior.contact_radius
    out.update(state='threat' if threat else 'clear_under_model',reason='known_size_finite_body_closest_approach')
    return out

def finite_estimate(current,previous,focal_px,center_x,prior):
    return inflate(estimate(current,previous,'closest_approach',focal_px,center_x),prior)

class FiniteThreatRule:
    def __init__(self,camera,prior):
        if not isinstance(prior,KnownSizePrior):raise ValueError('Explicit known-size prior required')
        self.prior=prior;self.core=ThreatRule(camera,'closest_approach')
        self.core.latest=inflate(self.core.latest,prior)

    def observe(self,frame,timestamp_s):
        record=self.core.observe(frame,timestamp_s)
        out=inflate(record['estimate'],self.prior)
        self.core.latest=out
        return dict(measurement=record['measurement'],estimate=dict(out))

    def sample(self,k):return self.core.sample(k)
    def reset(self):
        self.core.reset();self.core.latest=inflate(self.core.latest,self.prior)
    @property
    def latest(self):return self.core.latest
