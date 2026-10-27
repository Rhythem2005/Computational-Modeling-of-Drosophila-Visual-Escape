import numpy as np
from dashboard.simulation.avoidance.controller import Persistence,AvoidanceController
from dashboard.simulation.avoidance.perception import Track
from dashboard.simulation.avoidance.planning import LocalPlanner

def track(position,velocity,identity=0):return Track(identity,0,np.zeros(2),3.,np.array(position,dtype=float),np.array(velocity,dtype=float),True,[])

def test_closed_interval_persistence():
    p=Persistence()
    for k in range(20):assert not p.update(k,True)
    assert p.update(20,True);assert not p.update(21,False)

def test_unknown_never_becomes_clear_or_fallback_escape(settings):
    c=settings();policy=AvoidanceController(c,'circuit_planner');zero=np.zeros(3)
    for k in range(40):
        d=policy.update(k,[],True,['lost_track'],True,zero,zero,zero,[],True)
        assert d.unknown and not d.request and d.target is None
    assert policy.bouts==0

def test_planner_rejects_escape_into_second_object(settings):
    c=settings(prediction_horizon_ms=200);planner=LocalPlanner(c);zero=np.zeros(3)
    # Moving forward is blocked by the front object; retreat is blocked behind.
    tracks=[track([0,2.2,0],[0,-1,0]),track([0,-2.2,0],[0,1,0],1)]
    plan=planner.choose(tracks,zero,zero,zero,[],0,zero)
    assert abs(plan.target[1])<1e-12
    assert not np.array_equal(plan.target,zero) or not plan.feasible

def test_per_track_history_does_not_transfer_to_new_identity(settings):
    c=settings();policy=AvoidanceController(c,'simple_trigger');zero=np.zeros(3)
    a=track([0,10,0],[0,-10,0])
    for k in range(20):assert not policy.update(k,[a],True,[],False,zero,zero,zero,[],True).request
    b=track([0,10,0],[0,-10,0],1)
    assert not policy.update(20,[b],True,[],False,zero,zero,zero,[],True).request

def test_controller_recovers_and_initiates_second_bout_without_reset(settings):
    from dashboard.simulation.avoidance.planning import Plan
    c=settings();policy=AvoidanceController(c,'circuit_planner');zero=np.zeros(3)
    class StubPlan:
        def evaluate(self,*args):return 5.
        def choose(self,*args):return Plan(np.array([20.,0.,0.]),True,5.,'unit controller transition')
    policy.planner=StubPlan();requests=[]
    for k in range(63):
        if k<=20:t=track([0,2.5,0],[0,-10,0],0)
        elif k<=41:t=track([20,20,0],[0,0,0],0)
        else:t=track([0,2.5,0],[0,-10,0],1)
        if policy.update(k,[t],True,[],True,zero,zero,zero,[],True).request:requests.append(k)
    assert requests==[20,62];assert policy.bouts==2
