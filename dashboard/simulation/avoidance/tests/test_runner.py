"""Clock/evidence integration with a zero-output test double, never a research model."""
from types import SimpleNamespace
import numpy as np
from dashboard.simulation.avoidance.runner import Runner
from dashboard.simulation.avoidance.recording import audit_arrays
from dashboard.simulation.avoidance.contracts import Scenario

class ZeroCircuit:
    def __init__(self):
        self.ids=np.arange(321);self.freeze={'threshold':{'kind':'always_silent','value':None}}
        self.pipeline=self;self.encoder=self;self.controller=self;self.frames=[];self.times=[];self.drive=np.zeros(321)
    def encode(self,frames,times):
        n=len(frames);return SimpleNamespace(channels=np.zeros((n,2)),drive=np.zeros((n,321)),diagnostics={'valid':np.ones(n,dtype=bool)})
    def observe(self,frame,time_ms):
        self.frames.append(frame);self.times.append(time_ms);self.encoded=self.encode(self.frames,self.times)
    def sample(self,k):return dict(score=0.,state=np.zeros(321),drive=self.drive.copy(),sustained_score=0.,escape_event=False,escape_requested=False)
    def advance(self):pass
    def state_vector(self):return np.zeros(321)

def test_3d_runner_keeps_camera_and_terminal_clocks_and_no_action(settings):
    c=settings(duration_ms=100)
    s=Scenario('unit_clock_only',(0,0,0),(0,0,0),({'id':'unit','position':[5,20,3],'velocity':[0,0,0],'radius':1.5,'onset_ms':0},))
    r=Runner(c,'no_action',ZeroCircuit()).run(s)
    assert r['arrays']['fly_position'].shape==(101,3)
    assert r['arrays']['decision_times_ms'][-1]==99
    assert r['arrays']['controller_state_times_ms'][-1]==100
    np.testing.assert_array_equal(r['arrays']['fly_position'],np.zeros((101,3)))
    assert audit_arrays(c,s,r['arrays'],r['metrics'],r['commands'])

def test_terminal_live_packet_has_no_new_terminal_decision(settings):
    c=settings(duration_ms=100)
    s=Scenario('unit_terminal_only',(0,0,0),(0,0,0),({'id':'unit','position':[5,20,3],'velocity':[0,0,0],'radius':1.5,'onset_ms':0},))
    packets=[]
    class Observer:
        def publish(self,p):packets.append(p)
    Runner(c,'no_action',ZeroCircuit()).run(s,Observer())
    assert packets[-1]['time_ms']==100
    assert packets[-1]['decision_timestamp_ms']==99
    assert packets[-1]['neural_timestamp_ms']==100

def test_fractional_multi_object_contact_is_a_failure_and_is_preserved(settings):
    import pytest
    c=settings(duration_ms=300)
    s=Scenario('unit_swept_failure',(0,0,0),(0,0,0),(
        {'id':'unit_crossing','position':[0,5.025,0],'velocity':[0,-20,0],'radius':1.5,'onset_ms':0},
        {'id':'unit_remote','position':[20,20,10],'velocity':[0,0,0],'radius':1.5,'onset_ms':0}))
    r=Runner(c,'no_action',ZeroCircuit()).run(s)
    assert r['metrics']['failure']['kind']=='collision'
    assert r['metrics']['end_ms']==pytest.approx(151.25)
    assert r['metrics']['escape_success'] is False
    assert r['arrays']['decision_times_ms'][-1]==151
    assert r['arrays']['controller_state_times_ms'][-1]==151
    assert len(r['metrics']['per_object'])==2
    assert audit_arrays(c,s,r['arrays'],r['metrics'],r['commands'])

def test_independent_episode_cannot_reuse_hidden_state(settings):
    import pytest
    c=settings(duration_ms=100)
    s=Scenario('unit_reset',(0,0,0),(0,0,0),({'id':'unit','position':[5,20,3],'velocity':[0,0,0],'radius':1.5,'onset_ms':0},))
    runner=Runner(c,'no_action',ZeroCircuit());runner.run(s)
    with pytest.raises(ValueError,match='fresh reset circuit'):runner.run(s)
