import numpy as np
import pytest
from dataclasses import replace
from dashboard.simulation.room_flight.runner import RoomRunner
from dashboard.simulation.room_flight.recording import audit,save
from dashboard.simulation.room_flight.locomotion import RoomBehavior
from dashboard.simulation.avoidance.perception import Track

def test_room_runner_saves_pose_views_and_terminal_clocks(config,solid,scene,tmp_path):
    c=config();s=scene((solid(position=(0,-10,0)),));r=RoomRunner(c,'ordinary_motion').run(s)
    assert r['arrays']['sensor_frames'].shape==(6,6,24,24,3)
    assert r['arrays']['frames'].shape==(6,48,72,3)
    assert r['arrays']['decision_times_ms'][-1]==99
    assert r['arrays']['world_times_ms'][-1]==100
    assert r['arrays']['controller_states'].shape==(101,0)
    sensory=r['metrics']['sensory_support']
    assert sensory['captured_synchronized_frames']==6
    assert sum(sensory[k] for k in ('fully_motion_supported_frames','no_visible_target_frames','uncertain_tracking_frames'))==sensory['processed_tracking_frames']
    assert audit(c,s,r['arrays'],r['metrics'])
    save(tmp_path/'attempts'/'unit',r,c,s)
    assert (tmp_path/'episodes/unit.json').exists()

def test_repeated_bouts_keep_episode_clock(config):
    c=config();p=RoomBehavior(c,'surround_avoidance',());z=np.zeros(3)
    class Planner:
        def choose(self,*args):return np.zeros(3),True,5.
    p.planner=Planner();requests=[]
    for k in range(100):
        danger=k<25 or k>=60;pos=[0,-3,0] if danger else [0,-20,0];v=[0,20,0] if danger else [0,0,0]
        t=Track(0 if k<60 else 1,k,np.zeros(2),3,np.array(pos,dtype=float),np.array(v,dtype=float),True,[])
        d=p.update(k,[t],True,[],z,z,np.array([0,0,0,1]),z,[],True)
        if d.initiation:requests.append(k)
    assert requests==[20,80] and p.bouts==2 and p.index==100

def test_unknown_hidden_target_never_claims_clearance(config):
    c=config(allow_cruise_when_no_target_visible=False);p=RoomBehavior(c,'surround_avoidance',());z=np.zeros(3)
    d=p.update(0,[],True,['no_target_visible_not_clearance_proof'],z,z,[0,0,0,1],z,[],True)
    assert d.unknown and d.source=='uncertainty_brake' and not d.initiation

def test_normal_cruise_moves_without_an_escape_or_neural_reset(config,scene):
    c=config(cruise_body_velocity=(1,0,0));runner=RoomRunner(c,'ordinary_motion');r=runner.run(scene())
    assert r['arrays']['fly_position'][-1,0]>0
    assert not r['arrays']['escape_event'].any() and r['metrics']['avoidance_bouts']==0
    assert audit(c,scene(),r['arrays'],r['metrics'])
    with pytest.raises(ValueError,match='Fresh runner'):runner.run(scene())

def test_planning_accounts_for_queued_command_and_furniture(config,solid):
    from dashboard.simulation.room_flight.locomotion import RoomPlanner
    c=config();p=RoomPlanner(c,(solid('furniture',(0,3,0),shape='box'),));z=np.zeros(3)
    # A delay queue and current speed cannot be discarded when scoring a retreat.
    safe=p.evaluate(z,[],z,z,z,[],0)
    unsafe=p.evaluate(z,[],z,np.array([0.,20.,0.]),z,[(0,np.array([0.,20.,0.]))],0)
    assert safe>0 and unsafe<0

def test_terminal_telemetry_uses_latest_decision_mode_while_holding_camera(config,scene,monkeypatch):
    from dashboard.simulation.room_flight.locomotion import Command
    packets=[]
    class Observer:
        def publish(self,p):packets.append(p)
    def update(self,k,*args):return Command(None,'recovery' if k==99 else 'active','unknown' if k==99 else 'clear_under_model',False,k==99,None,'unit')
    monkeypatch.setattr(RoomBehavior,'update',update)
    r=RoomRunner(config(),'ordinary_motion').run(scene(),Observer())
    assert packets[-1]['time_ms']==100 and packets[-1]['decision_timestamp_ms']==99
    assert packets[-1]['gate_state']=='recovery' and packets[-1]['rule_state']=='unknown'
    assert packets[-1]['camera_timestamp_ms']<99
    assert packets[-1]['gate_state']==r['arrays']['gate_state'][-1]
