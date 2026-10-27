"""Approved analytic-rule tests; artificial image/measurement inputs only."""
import numpy as np
import pytest
from connectome.scripts.collision_threat_v1.features import Camera
from connectome.scripts.collision_threat_v1.threat_rule import estimate,ThreatRule
from connectome.scripts.collision_threat_v1.hybrid import HybridGate,Driver

@pytest.fixture
def camera():return Camera(256,256,128.,128.,160.,60.,128,4)

def measured(q):
    r=160/q[1]
    return dict(radius_px=r,centroid_x_px=128+q[0]*r,motion_valid=True,
                measurement_valid=True,interval_s=1/60,reasons=[])

@pytest.mark.parametrize('q,prev,state',[
    ([0.,10.],[0.,11.],'threat'),
    ([1.,10.],[1.,20.],'threat'),
    ([1.2,10.],[1.2,11.],'clear_under_model'),
    ([-1.,9.],[-2.,10.],'clear_under_model'),
    ([0.,11.],[0.,10.],'clear_under_model'),
    ([0.,10.],[0.,10.],'clear_under_model')])
def test_exact_analytic_cases(q,prev,state):
    r=estimate(measured(q),measured(prev),'closest_approach',160.,128.)
    assert r['state']==state

def test_boundary_is_object_radius_not_finite_fly_safety():
    boundary=estimate(measured([1.,10.]),measured([1.,20.]),'closest_approach',160.,128.)
    outside=estimate(measured([1.2,10.]),measured([1.2,11.]),'closest_approach',160.,128.)
    assert boundary['d_closest_in_object_radii']==1.
    assert outside['point_observer_proxy'] and outside['state']=='clear_under_model'

def test_expansion_ablation_removes_geometry_only():
    current=measured([-1.,9.]);previous=measured([-2.,10.])
    assert estimate(current,previous,'expansion_only',160.,128.)['state']=='threat'
    assert estimate(current,previous,'closest_approach',160.,128.)['state']=='clear_under_model'

def test_unknown_and_invalid_do_not_turn_into_clear():
    current=measured([0.,10.]);current.update(motion_valid=False,reasons=['timestamp_gap'])
    out=estimate(current,None,'closest_approach',160.,128.)
    assert out['state']=='unknown' and out['d_closest_in_object_radii'] is None

def test_nonfinite_calculation_aborts():
    current=measured([0.,10.]);current['centroid_x_px']=float('inf')
    with pytest.raises(FloatingPointError):estimate(current,measured([0.,11.]),'closest_approach',160.,128.)

def test_hybrid_pending_survives_clear_and_latches_first_physical_event():
    gate=HybridGate();events=[]
    for k in range(100):
        out=gate.update(k,k>=20,'threat' if k>=40 else 'clear_under_model',k>=40)
        if out['escape_event']:events.append(k)
    assert events==[40] and gate.internal_request_ms==20 and gate.physical_request_ms==40
    assert not gate.fallback

def test_unknown_fallback_is_recorded_once():
    gate=HybridGate();events=[]
    for k in range(60):
        out=gate.update(k,k>=20,'unknown' if k>=25 else 'clear_under_model',False)
        if out['fallback_event']:events.append(k)
    assert events==[25] and gate.fallback and gate.internal_request_ms==20

def test_silent_upstream_cannot_bypass_gate():
    gate=HybridGate()
    assert not any(gate.update(k,False,'threat',True)['escape_event'] for k in range(100))

def test_hybrid_does_not_use_stale_ever_latched_threat():
    gate=HybridGate();events=[]
    for k in range(80):
        sustained=k<30 or k>=60
        state='threat' if sustained else 'clear_under_model'
        if gate.update(k,k>=40,state,sustained)['escape_event']:events.append(k)
    assert events==[60]

def test_invalid_gate_clock_and_endpoint_abort():
    gate=HybridGate()
    with pytest.raises(ValueError):gate.update(1,False,'unknown',False)
    for k in range(1000):gate.update(k,False,'unknown',False)
    with pytest.raises(ValueError):gate.update(1000,False,'unknown',False)

def circle(radius,cx=128):
    y,x=np.ogrid[:256,:256];a=np.full((256,256),128,dtype=np.uint8)
    a[(x-cx)**2+(y-128)**2<=radius**2]=64
    return a

def test_image_only_rule_closed_twenty_ms_and_reset(camera):
    rule=ThreatRule(camera,'closest_approach');events=[]
    frames={0:circle(10),17:circle(11),34:circle(12),50:circle(13)}
    for k in range(70):
        if k in frames:
            ts={0:0.,17:1/60,34:2/60,50:3/60}[k]
            rule.observe(frames[k],ts)
        if rule.sample(k)['escape_event']:events.append(k)
    assert events==[37]
    rule.reset();rule.observe(circle(10),0.)
    assert rule.sample(0)['state']=='unknown'

def test_future_frame_access_is_error_not_fallback(camera):
    rule=ThreatRule(camera,'closest_approach');rule.observe(circle(10),1/60)
    with pytest.raises(ValueError,match='Future'):rule.sample(0)

def test_driver_resets_by_fresh_episode_construction(camera):
    first=Driver('closest_approach_rule',None,camera,{})
    first.observe(circle(10),0.);first.sample(0,np.zeros(321))
    second=Driver('closest_approach_rule',None,camera,{})
    second.observe(circle(10),0.)
    assert not second.sample(0,np.zeros(321))['escape_requested']

def test_future_pixels_do_not_change_earlier_rule_outputs(camera):
    def prefix(changed):
        rule=ThreatRule(camera,'closest_approach');out=[]
        for k in range(50):
            if k in (0,17,34):
                n={0:0,17:1,34:2}[k]
                frame=np.full((256,256),128,dtype=np.uint8) if changed and k==34 else circle(10+n)
                rule.observe(frame,n/60)
            out.append(rule.sample(k))
        return out
    assert prefix(False)[:34]==prefix(True)[:34]

def test_rule_cannot_activate_without_valid_history(camera):
    rule=ThreatRule(camera,'expansion_only');rule.observe(circle(10),0.)
    assert not any(rule.sample(k)['escape_event'] for k in range(16))
    rule.observe(circle(12),2/60)
    assert rule.latest['state']=='unknown'
