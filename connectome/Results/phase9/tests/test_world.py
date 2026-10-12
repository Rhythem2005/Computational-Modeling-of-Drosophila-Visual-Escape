from copy import deepcopy
import json
import numpy as np
import pytest
from connectome.scripts.phase9.config import load_config,fixtures,validate_config,BASE
from connectome.scripts.phase9.world import World,swept_contact,stationary_danger,render_camera
from connectome.scripts.phase9.runner import ClosedLoopRunner
from connectome.scripts.phase9.activity_io import save_episode,load_episode
from connectome.scripts.phase4 import simulator
from connectome.scripts.phase6.encoder import causal_hold


@pytest.mark.parametrize("p,d,r,hit",[([5,0],[-10,0],1,.4),([2,1],[-4,0],1,.5),([1,0],[0,0],1,0),([2,0],[0,0],1,None),([2,0],[1,0],1,None),([2,0],[-1,0],1,1),([10,2],[-20,0],1,None)])
def test_analytic_sweeps_tangent_contact_tunneling(p,d,r,hit):
    actual,clearance=swept_contact(p,d,r)
    assert actual is None if hit is None else actual==pytest.approx(hit)
    assert np.isfinite(clearance)


def test_swept_geometry_invalid_and_closest_clearance():
    with pytest.raises(ValueError): swept_contact([np.nan,0],[1,0],1)
    with pytest.raises(ValueError): swept_contact([1,0],[1,0],0)
    hit,clearance=swept_contact([-10,3],[20,0],1)
    assert hit is None and clearance==2


@pytest.mark.parametrize("name,danger",[("world_head_on",True),("world_left",True),("world_right",True),("world_static",False),("world_near_miss",False)])
def test_geometry_only_labels(name,danger):
    scenario=next(s for s in fixtures() if s["scenario_id"]==name)
    metric=stationary_danger(load_config(),scenario)
    assert metric["danger"] is danger
    if danger: assert 900<metric["stationary_contact_ms"]<1000


def test_actuator_delay_latch_bounds_and_no_step_after_end():
    c=load_config();w=World(c,fixtures()[3])
    w.request(.5);assert w.request(-.5) is False
    for _ in range(21):w.step()
    assert w.time_ms==21 and np.all(w.fly==0) and w.first_motion_ms is None
    w.step();assert w.first_motion_ms==21 and w.fly[0]>0 and w.fly[1]<0
    assert w.activate_ms==20 and w.turn==.5
    while not w.done:w.step()
    assert w.truncated and not w.terminated and w.speed==c["escape_speed_max"]
    assert w.metrics()["false_alarm"] and w.metrics()["escape_success"] is None
    with pytest.raises(ValueError):w.step()
    with pytest.raises(ValueError):w.request(0)
    with pytest.raises(ValueError):World(c,fixtures()[3]).request(1.01)


def test_collision_partial_step_boundary_and_initial_overlap():
    c=load_config();s=deepcopy(fixtures()[0]);s["obstacles"][0].update(position=[0,2.5],velocity=[0,-2000])
    w=World(c,s)
    while not w.done:w.step()
    assert w.terminated and w.failure["kind"]=="collision" and w.time_ms==pytest.approx(200.25)
    assert w.min_clearance==pytest.approx(0,abs=1e-12)
    s["obstacles"][0]["position"]=[0,1]
    overlap=World(c,s);assert overlap.terminated and overlap.time_ms==0
    c["bounds_xy"]=[[-.6,.6],[-.6,.6]]
    boundary=World(c,fixtures()[3]);boundary.request(0)
    while not boundary.done:boundary.step()
    assert boundary.failure["kind"]=="boundary" and boundary.fly[1]==pytest.approx(-.1)


def test_horizon_contact_is_collision_not_survival():
    c=load_config();s=deepcopy(fixtures()[0]);s["obstacles"][0]["velocity"]=[0,-22.5]
    w=World(c,s)
    while not w.done:w.step()
    assert w.terminated and not w.truncated
    assert w.time_ms==pytest.approx(1000,abs=1e-8)
    assert not w.metrics()["survived_horizon"] and not w.metrics()["escape_success"]


def test_invalid_config_scenario():
    c=load_config();c["escape_speed_max"]=float('inf')
    with pytest.raises(ValueError):validate_config(c)
    s=deepcopy(fixtures()[0]);s["obstacles"].append(s["obstacles"][0])
    with pytest.raises(ValueError):World(load_config(),s)


def test_camera_perspective_translation_behind_and_current_only():
    c=load_config()
    a,_=render_camera(c,np.zeros(2),np.array([[0,20]]),[1.5])
    b,_=render_camera(c,np.array([3,-10]),np.array([[0,20]]),[1.5])
    assert np.count_nonzero(b==64)<np.count_nonzero(a==64)
    y,x=np.nonzero(b==64);assert x.mean()<128
    invisible,diag=render_camera(c,np.zeros(2),np.array([[0,-1]]),[1.5])
    assert np.all(invisible==128) and diag["near_or_behind"]==1
    translated,_=render_camera(c,np.array([5,5]),np.array([[5,25]]),[1.5])
    np.testing.assert_array_equal(a,translated)


@pytest.fixture(scope="module")
def runner():return ClosedLoopRunner()


@pytest.fixture(scope="module")
def primary(runner):return runner.run(fixtures()[0])


def test_streamed_full_batch_frozen_interfaces(runner,primary):
    a=primary["arrays"]
    encoded=runner.pipeline.encoder.encode(a["frames"],a["frame_timestamps_s"])
    batch=runner.pipeline.run_encoded(encoded,1000)
    np.testing.assert_array_equal(a["states"],batch.states)
    np.testing.assert_array_equal(a["step_drive_unscaled"],batch.step_drive_unscaled)
    np.testing.assert_array_equal(a["step_input_scaled"],batch.step_input_scaled)
    assert np.all(a["turn_command"]==0) and primary["metrics"]["direct_dn_input_max"]==0
    assert primary["metrics"]["streamed_offline_decoder_equal"] and primary["metrics"]["causal_prefix_batch_input_equal"]


def test_fractional_timing_and_action_future_prefix(runner,primary):
    a=primary["arrays"]
    assert a["step_frame_indices"][16]==0 and a["step_frame_indices"][17]==1
    frame0=a["frames"][0].copy()
    altered=deepcopy(fixtures()[0]);altered["obstacles"][0]["velocity"]=[0,-50]
    other=runner.run(altered)["arrays"]
    keep=a["frame_timestamps_s"]<=.2
    np.testing.assert_array_equal(a["frames"][keep],other["frames"][other["frame_timestamps_s"]<=.2])
    np.testing.assert_array_equal(a["states"][:201],other["states"][:201])
    np.testing.assert_array_equal(frame0,a["frames"][0])
    assert a["neural_times_ms"][-1]<=primary["metrics"]["end_ms"] and np.all(a["decision_times_ms"]<1000)


def test_fractional_terminal_neural_state_and_decision_cutoff(runner):
    scenario=deepcopy(fixtures()[0])
    scenario["obstacles"][0].update(position=[0,2.5],velocity=[0,-2000])
    run=runner.run(scenario);a=run["arrays"];m=run["metrics"]
    assert m["terminated"] and m["end_ms"]==pytest.approx(200.25)
    assert a["world_times_ms"][-1]==pytest.approx(200.25)
    assert a["neural_times_ms"][-1]==200 and a["decision_times_ms"][-1]==200
    assert len(a["step_times_ms"])==200 and np.all(a["states"]==0)
    assert m["dangerous_miss"] and not m["escape_success"]


@pytest.mark.parametrize("seed",[55010,55011,55012,55013,55014])
def test_synthetic_seed_streaming_equivalence(runner,seed):
    run=runner.run(fixtures()[1],condition=load_config()["secondary_condition"],seed=seed)
    a=run["arrays"];m=run["metrics"]
    assert np.all(np.abs(a["turn_command"])<=1) and m["direct_dn_input_max"]==0
    assert m["causal_prefix_batch_input_equal"] and m["streamed_offline_decoder_equal"]
    assert run["action"]["threshold_status"]=="primary_frozen_threshold_reused_uncalibrated_spatial_fixture"


def test_scripted_action_changes_later_observations():
    c=load_config();s=fixtures()[0];on=World(c,s);off=World(c,s)
    for _ in range(300):on.step();off.step()
    before_on,_=render_camera(c,on.fly,on.obstacles,on.radii)
    before_off,_=render_camera(c,off.fly,off.obstacles,off.radii)
    np.testing.assert_array_equal(before_on,before_off)
    on.request(0)
    for _ in range(100):on.step();off.step()
    after_on,_=render_camera(c,on.fly,on.obstacles,on.radii)
    after_off,_=render_camera(c,off.fly,off.obstacles,off.radii)
    assert np.any(after_on!=after_off) and not np.array_equal(on.fly,off.fly)


def test_repeat_and_saved_schema_roundtrip(runner,primary):
    repeat=runner.run(fixtures()[0])
    assert primary["metrics"]==repeat["metrics"] and primary["action"]==repeat["action"]
    for k,v in primary["arrays"].items():np.testing.assert_array_equal(v,repeat["arrays"][k])
    directory=BASE / "results/test_roundtrip"
    save_episode(directory,"fixture",primary,overwrite=True)
    with pytest.raises(FileExistsError):save_episode(directory,"fixture",primary)
    loaded=load_episode(directory,"fixture")
    assert loaded["metrics"]==primary["metrics"]
    with pytest.raises(ValueError):save_episode(BASE.parent / "phase8/results","bad",primary)
    path=directory / "fixture_action.json"; original=path.read_text();path.write_text('{}')
    try:
        with pytest.raises(ValueError):load_episode(directory,"fixture")
    finally:path.write_text(original)
