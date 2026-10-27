"""Analytic/unit checks only; no additional physical episodes or seed selection."""
import inspect
import numpy as np
import pytest
from connectome.scripts.collision_threat_v1.features import Camera
from connectome.scripts.collision_threat_v1.threat_rule import estimate as point_estimate
from connectome.scripts.collision_threat_v1.hybrid import HybridGate
from connectome.scripts.collision_threat_v2.rule import KnownSizePrior,FiniteThreatRule,finite_estimate,inflate
from connectome.scripts.collision_threat_v2.gate import RetirementGate
from connectome.scripts.collision_threat_v2.driver import Driver

@pytest.fixture
def prior():return KnownSizePrior(1.5,.5)
@pytest.fixture
def camera():return Camera(256,256,128.,128.,160.,60.,128,4)

def measured(q):
    r=160/q[1]
    return dict(radius_px=r,centroid_x_px=128+q[0]*r,motion_valid=True,measurement_valid=True,
                interval_s=1/60,reasons=[])

def test_derived_boundary_and_declared_units(prior):
    assert prior.contact_radius==1+.5/1.5==4/3

@pytest.mark.parametrize('bad',[None,0.,-1.,float('nan'),float('inf'),True,2.])
def test_unapproved_object_prior_rejected(bad):
    with pytest.raises(ValueError):KnownSizePrior(bad,.5)

@pytest.mark.parametrize('bad',[None,0.,-1.,float('nan'),True,1.])
def test_unapproved_self_prior_rejected(bad):
    with pytest.raises(ValueError):KnownSizePrior(1.5,bad)

def test_missing_prior_rejected(camera):
    with pytest.raises(ValueError):FiniteThreatRule(camera,None)
    with pytest.raises(ValueError):Driver('finite_standalone_v2',None,camera,{},None)

def test_point_clear_can_be_finite_body_contact(prior):
    d=(1+prior.contact_radius)/2
    a,b=measured([d,10.]),measured([d,20.])
    assert point_estimate(a,b,'closest_approach',160.,128.)['state']=='clear_under_model'
    result=finite_estimate(a,b,160.,128.,prior)
    assert result['state']=='threat' and not result['point_observer_proxy']

def test_geometric_tangency_included_without_fitted_tolerance(prior):
    # Direct exact boundary kernel check; rasterization errors are not a new epsilon.
    point=dict(state='clear_under_model',reason='point_observer_closest_approach',
               growing=True,t_closest_s=.5,d_closest_in_object_radii=prior.contact_radius)
    assert inflate(point,prior)['state']=='threat'
    point['d_closest_in_object_radii']=np.nextafter(prior.contact_radius,np.inf)
    assert inflate(point,prior)['state']=='clear_under_model'

@pytest.mark.parametrize('q,previous,state',[
    ([0.,10.],[0.,20.],'threat'),([2.,10.],[2.,20.],'clear_under_model'),
    ([0.,20.],[0.,10.],'clear_under_model'),([0.,10.],[0.,10.],'clear_under_model')])
def test_finite_stationary_approach_recede_and_outside(prior,q,previous,state):
    assert finite_estimate(measured(q),measured(previous),160.,128.,prior)['state']==state

def test_undefined_stays_unknown_and_nonfinite_aborts(prior):
    a=measured([0.,10.]);a.update(motion_valid=False,reasons=['timestamp_gap'])
    assert finite_estimate(a,None,160.,128.,prior)['state']=='unknown'
    a=measured([0.,10.]);a['centroid_x_px']=float('inf')
    with pytest.raises(FloatingPointError):finite_estimate(a,measured([0.,20.]),160.,128.,prior)

def test_normalization_does_not_observe_unknown_object_scale():
    def pixels(x,y,r):return ((128+160*x/y-128)/(160*r/y),160/(160*r/y))
    np.testing.assert_array_equal(pixels(3.,15.,1.5),pixels(6.,30.,3.))

def test_observation_api_contains_no_episode_radius_or_labels():
    assert list(inspect.signature(FiniteThreatRule.observe).parameters)==['self','frame','timestamp_s']

def test_retirement_stops_late_unknown_fallback():
    gate=RetirementGate();physical=[];retire=[]
    for k in range(100):
        state='clear_under_model' if k<30 else 'unknown'
        out=gate.update(k,k>=20,state)
        if out['escape_event']:physical.append(k)
        if out['retirement_event']:retire.append(k)
    assert retire==[20] and physical==[] and gate.phase=='retired_clear'
    assert gate.internal_request_ms==20 and gate.physical_request_ms is None

def test_fresh_threat_rearms_with_new_epoch_after_retirement():
    gate=RetirementGate();events=[];rearms=[]
    for k in range(120):
        state='clear_under_model' if k<30 else 'unknown' if k<50 else 'threat'
        out=gate.update(k,k>=20,state)
        if out['escape_event']:events.append(k)
        if out['rearm_event']:rearms.append((k,out['candidate_epoch']))
    assert events==[70] and rearms==[(70,2)]
    assert gate.retirements==[20.] and gate.generations==[20.,70.]

def test_unknown_before_retirement_keeps_conservative_fallback():
    gate=RetirementGate();events=[]
    for k in range(80):
        out=gate.update(k,k>=20,'unknown')
        if out['fallback_event']:events.append(k)
    assert events==[20] and gate.phase=='physical_latched' and gate.retirements==[]

def test_old_gate_keeps_original_failure_for_comparison():
    gate=HybridGate();events=[]
    for k in range(80):
        out=gate.update(k,k>=20,'clear_under_model' if k<40 else 'unknown',False)
        if out['escape_event']:events.append(k)
    assert events==[40]

def test_current_clear_required_not_stale_history():
    gate=RetirementGate();retire=[]
    for k in range(80):
        state='clear_under_model' if k<20 or k>=21 else 'unknown'
        out=gate.update(k,k>=22,state)
        if out['retirement_event']:retire.append(k)
    assert retire==[41]

def test_ever_latched_threat_cannot_rearm_after_clear():
    gate=RetirementGate();events=[]
    for k in range(120):
        state='threat' if k<30 or k>=70 else 'clear_under_model'
        out=gate.update(k,k>=40,state)
        if out['escape_event']:events.append(k)
    assert gate.retirements==[50.] and events==[90]

def test_unknown_breaks_both_evidence_histories():
    gate=RetirementGate()
    for k in range(50):
        state='threat' if k<20 else 'unknown' if k==20 else 'clear_under_model'
        out=gate.update(k,False,state)
        if k==20:assert not out['current_clear_sustained'] and not out['current_threat_sustained']
        if k==40:assert not out['current_clear_sustained']
        if k==41:assert out['current_clear_sustained']

def test_silent_upstream_cannot_arm_or_bypass():
    gate=RetirementGate()
    for k in range(100):assert not gate.update(k,False,'threat')['escape_event']
    assert gate.phase=='unarmed' and gate.internal_request_ms is None

def test_physical_latch_and_terminal_clock():
    gate=RetirementGate();events=[]
    for k in range(1000):
        out=gate.update(k,k>=20,'threat' if k<40 else 'unknown')
        if out['escape_event']:events.append(k)
    assert events==[20]
    with pytest.raises(ValueError):gate.update(1000,True,'unknown')

@pytest.mark.parametrize('k,state',[(True,'unknown'),(0.,'unknown'),(1,'unknown'),(0,'broken')])
def test_bad_clock_and_state_abort(k,state):
    with pytest.raises(ValueError):RetirementGate().update(k,False,state)

def image(radius,cx=128):
    y,x=np.ogrid[:256,:256];a=np.full((256,256),128,dtype=np.uint8)
    a[(x-cx)**2+(y-128)**2<=radius**2]=64
    return a

def test_finite_prefix_invariance_reset_and_future_guard(camera,prior):
    def outputs(changed):
        rule=FiniteThreatRule(camera,prior);out=[]
        for k in range(55):
            if k in (0,17,34):
                n={0:0,17:1,34:2}[k]
                frame=np.full((256,256),128,dtype=np.uint8) if changed and k==34 else image(10+n)
                rule.observe(frame,n/60)
            out.append(rule.sample(k))
        return out
    assert outputs(False)[:34]==outputs(True)[:34]
    rule=FiniteThreatRule(camera,prior);rule.observe(image(10),0.);rule.sample(0)
    rule.reset();rule.observe(image(10),0.)
    assert rule.sample(0)['state']=='unknown'
    rule.reset();rule.observe(image(10),1/60)
    with pytest.raises(ValueError):rule.sample(0)

def test_gate_reset_drops_pending_retirement_and_epochs():
    gate=RetirementGate()
    for k in range(30):gate.update(k,k>=20,'clear_under_model')
    gate.reset()
    assert gate.phase=='unarmed' and gate.epoch==0 and gate.retirements==[]
    assert not gate.update(0,False,'unknown')['escape_requested']

def test_new_driver_does_not_pass_prior_to_point_rule(camera,prior):
    point=Driver('point_standalone_v1',None,camera,{},prior)
    finite=Driver('finite_standalone_v2',None,camera,{},prior)
    assert point.prior is None and finite.prior==prior
