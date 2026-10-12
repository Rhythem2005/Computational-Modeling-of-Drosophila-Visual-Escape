from copy import deepcopy
from dataclasses import replace
import json
import numpy as np
import pytest

from connectome.scripts.phase6.encoder import digest, load_mapping
from connectome.scripts.phase7.pipeline import FrozenPipeline
from connectome.scripts.phase8.decoder import Threshold, InitiationDecoder, decode_score
from connectome.scripts.phase8.completion.controls import features_from_encoded, fit_linear, linear_score
from connectome.scripts.phase8.completion.calibration import make_plan, select_final
from connectome.scripts.phase8.completion.spatial import assign_fields, frame_drive, simulate_spatial
from connectome.scripts.phase8.completion.decoder import steering_commands
from connectome.scripts.phase8.completion.evidence import ROOT


@pytest.fixture(scope="module")
def pipeline():
    return FrozenPipeline()


@pytest.fixture(scope="module")
def encoded(pipeline):
    return pipeline.load_frozen_encoded("train_f0000_looming")


def fixture_config(x=64):
    return dict(stimulus_id="spatial_fixture", stimulus_type="looming", width=256, height=256, fps=60,
        duration_ms=1000, initial_position=[x,128], initial_radius=10, background_intensity=128, object_intensity=64,
        shape="circle", start_time_ms=200, random_seed=0,
        expansion_params=dict(f_R=500,Z0=50,v=25,t_onset_ms=200,min_distance=1))


def record(sid, label, cohort="train", role=None):
    score = np.zeros(1000)
    if label: score[250:] = 1.0
    return dict(scenario_id=sid, group_id=sid.split("_")[0], split=cohort, cohort=cohort, label=label,
                role=role or ("looming" if label else "static_initial"), times_ms=np.arange(1000,dtype=np.float64),
                scores={key: score.copy() for key in ("circuit", "feature_only", "linear_temporal")})


def test_filter_matches_independent_per_neuron_euler(pipeline, encoded):
    t, feature, filtered = features_from_encoded(encoded)
    from connectome.scripts.phase6.encoder import causal_hold
    full = causal_hold(encoded.drive, encoded.timestamps_s, t / 1000)
    z = np.zeros_like(full)
    for k in range(999): z[k+1] = .9*z[k] + .04*full[k]
    assigned = np.array(pipeline.encoder.mapping["channel_index"])
    expected = np.column_stack([z[:,assigned==ch].mean(axis=1) for ch in (0,1)])
    np.testing.assert_allclose(filtered,expected,rtol=1e-14,atol=1e-15)
    assert np.all(filtered[0] == 0)
    assert np.all(feature[t<=200] == 0)


def test_control_prefix_future_causality(encoded):
    _, _, a = features_from_encoded(encoded)
    altered = deepcopy(encoded)
    altered.drive[30:] = 0
    _, _, b = features_from_encoded(altered)
    np.testing.assert_array_equal(a[:501],b[:501])
    assert np.any(a[501:] != b[501:])


def test_linear_fit_known_nonnegative_solution():
    rows = []
    for k,(x,y) in enumerate(([0,0],[1,0],[0,1],[1,1])):
        feature = np.tile([x,y],(1000,1)).astype(float)
        rows.append(dict(scenario_id=f"s{k}",split="train",cohort="train",label=int(x>0),filtered_features=feature))
    fit=fit_linear(rows)
    assert fit["weights"][0] > .99 and fit["weights"][1] < 1e-5 and fit["bias"] == 0 and fit["trainable_parameters"]==2
    assert np.all(np.asarray(fit["weights"])>=0)
    with pytest.raises(ValueError): fit_linear([dict(rows[0],split="validation")])


def test_calibration_gate_train_validation_separation():
    training=[record("t0",0),record("t1",1)]
    plan=make_plan(training,"circuit")
    validation=[record("v0",0,"validation"),record("v1",1,"validation")]
    with pytest.raises(ValueError): select_final(plan,validation,"circuit",{})
    gate=dict(status="PASS",integrated_models=["feature_only","linear_temporal"],same_encoded_input_verified=True)
    result=select_final(plan,validation,"circuit",gate)
    assert result["threshold"]["kind"]=="finite" and result["selected_assessment"]["timely_tpr"]==1 and result["selected_assessment"]["full_episode_fpr"]==0
    with pytest.raises(ValueError): select_final(plan,[record("test",0,"test")],"circuit",gate)
    with pytest.raises(ValueError): make_plan(validation,"circuit")


def test_early_event_is_not_reset_for_validation():
    training=[record("t0",0),record("t1",1)]
    validation=[record("v0",0,"validation"),record("v1",1,"validation")]
    validation[1]["scores"]["circuit"][:40]=1
    gate=dict(status="PASS",integrated_models=["feature_only","linear_temporal"],same_encoded_input_verified=True)
    result=select_final(make_plan(training,"circuit"),validation,"circuit",gate)
    finite=next(r for r in result["assessments"] if r["threshold"]["kind"]=="finite")
    assert finite["timely_tpr"]==0 and finite["pre_onset_decisions"]==1


@pytest.mark.parametrize("seed",[55010,55011,55012,55013,55014])
def test_mapping_seed_reproducibility_membership_independence(seed):
    nodes=load_mapping()["nodes"]
    a=assign_fields(nodes,seed)
    b=assign_fields(list(reversed(nodes)),seed)
    assert digest(a)==digest(b) and len(a["fields"])==311 and a["biological_retinotopy"] is False
    altered=deepcopy(nodes)
    for n in altered: n.update(outgoing_DN_weight=1e9,modeled_outcome=123)
    assert digest(assign_fields(altered,seed))==digest(a)
    for f in a["fields"]:
        assert -1<=f["center_y"]<=1
        assert (-1<=f["center_x"]<=0) if f["side"]=="left" else (0<=f["center_x"]<=1)


def test_mapping_rejects_seed_search():
    with pytest.raises(ValueError): assign_fields(load_mapping()["nodes"],42)


def test_spatial_frame_only_causality_and_dn_zero(pipeline):
    from connectome.scripts.phase5.generator import generate_stimulus
    frames,ts=generate_stimulus(fixture_config())
    mapping=assign_fields(pipeline.encoder.mapping["nodes"],55010)
    global_out,drive,centroid=frame_drive(pipeline.encoder,frames,ts,mapping)
    altered=frames.copy(); altered[30:]=128
    _,changed,_=frame_drive(pipeline.encoder,altered,ts,mapping)
    np.testing.assert_array_equal(drive[:30],changed[:30])
    dn=np.array(pipeline.encoder.mapping["channel_index"])<0
    assert np.all(drive[:,dn]==0) and np.max(drive)<=1 and np.min(drive)>=0
    assert np.max(drive)<=np.max(global_out.drive)
    assert np.all(centroid[:,0]<0)


def test_spatial_tampered_assignment_rejected(pipeline):
    from connectome.scripts.phase5.generator import generate_stimulus
    frames,ts=generate_stimulus(fixture_config())
    mapping=assign_fields(pipeline.encoder.mapping["nodes"],55010)
    mapping["fields"][0]["center_x"]=999
    with pytest.raises(ValueError): frame_drive(pipeline.encoder,frames,ts,mapping)


def decoded_dn(left,right):
    d=decode_score(np.arange(100,dtype=float),np.ones(100),100.0,Threshold("finite",.5))
    d.dn_body_ids=np.array([10228,10584],dtype=np.int64)
    d.dn_activity=np.column_stack([np.ones(100)*left,np.ones(100)*right])
    return d


def test_steering_identity_neutral_bound_mirror_and_latch():
    a=decoded_dn(3,1)
    primary=steering_commands(a,condition="uniform_population")
    assert np.all(primary["turn_command"]==0)
    steer=steering_commands(a,condition="synthetic_fields_within_type_and_side_v1")
    assert np.all(steer["turn_command"][:20]==0) and np.all(steer["turn_command"][20:]==.5)
    b=decoded_dn(1,3)
    np.testing.assert_array_equal(steer["turn_command"],-steering_commands(b,condition="synthetic_fields_within_type_and_side_v1")["turn_command"])
    a.dn_activity[21:]=[0,100]
    np.testing.assert_array_equal(steer["turn_command"],steering_commands(a,condition="synthetic_fields_within_type_and_side_v1")["turn_command"])
    zero=steering_commands(decoded_dn(0,0),condition="synthetic_fields_within_type_and_side_v1")
    assert np.all(zero["turn_command"]==0)


def test_actual_spatial_pipeline_determinism_and_time(pipeline):
    from connectome.scripts.phase5.generator import generate_stimulus
    frames,ts=generate_stimulus(fixture_config())
    mapping=assign_fields(pipeline.encoder.mapping["nodes"],55010)
    a=simulate_spatial(pipeline,frames,ts,1000.,mapping)
    b=simulate_spatial(pipeline,frames,ts,1000.,mapping)
    np.testing.assert_array_equal(a["states"],b["states"])
    assert a["states"].shape==(1001,321) and a["activation_clipped_fraction"]==0
    assert np.all(a["states"][a["times_ms"]<=200]==0)


def test_steering_gain_normalization_and_invalid_scale():
    a=decoded_dn(6,2)
    result=steering_commands(a,condition="synthetic_fields_within_type_and_side_v1",gains=[3,1])
    assert np.all(result["turn_command"]==0)
    with pytest.raises(ValueError): steering_commands(a,condition="synthetic_fields_within_type_and_side_v1",gains=[0,1])


def test_calibrated_wrapper_freeze_proof_and_mapping_gate(tmp_path,monkeypatch):
    from connectome.scripts.phase8.completion import decoder as module
    from connectome.scripts.phase8.completion.controls import load_config
    from connectome.scripts.phase8.completion.evidence import file_hash
    monkeypatch.setattr(module,"verify_checkpoint",lambda: {"status":"PASS"})
    proof=tmp_path/"control_proof.json"; proof.write_text('{"synthetic_fixture":true}')
    config_path=ROOT/"connectome/phase8/completion/completion_config.yaml"
    payload=dict(status="calibrated_frozen",completion_config_sha256=digest(load_config()),
                 sources_sha256={str(config_path.relative_to(ROOT)):file_hash(config_path)},
                 prerequisite_artifacts_sha256={str(proof):file_hash(proof)},
                 models={name:dict(threshold=Threshold("finite",.5).as_dict()) for name in ("circuit","feature_only","linear_temporal")},
                 control_gate=dict(status="PASS"),steering_normalization=dict(gains=[1.,1.]))
    payload["payload_sha256"]=digest(payload)
    path=tmp_path/"freeze.json"; path.write_text(json.dumps(payload))
    wrapper=module.CalibratedDecoder(path)
    ids=np.array(load_mapping()["body_ids"],dtype=np.int64)
    states=np.zeros((1001,321)); states[:,np.isin(ids,[10010,10001])]=1
    times=np.arange(1001,dtype=float)
    d,s,action=wrapper.decode_activity(times,states,ids,1000.)
    assert action["threshold_status"]=="validation_selected_frozen" and action["steering"]==0 and d.first_event_ms==20
    with pytest.raises(ValueError): wrapper.decode_activity(times,states,ids,1000.,condition="synthetic_fields_within_type_and_side_v1")
    proof.write_text("tampered")
    with pytest.raises(ValueError): module.CalibratedDecoder(path)


def test_completed_action_roundtrip_and_no_old_output_overwrite(tmp_path,monkeypatch):
    from connectome.scripts.phase8.completion import activity_io as module
    monkeypatch.setattr(module,"BASE",tmp_path)
    d=decoded_dn(3,1)
    s=steering_commands(d,condition="synthetic_fields_within_type_and_side_v1")
    action=dict(d.action(),steering=.5)
    paths=module.save_action(tmp_path/"actions","sample",d,s,action,{"synthetic_fixture":True})
    with np.load(paths[0],allow_pickle=False) as saved:
        assert saved["schema_version"].item()=="1.2"
        np.testing.assert_array_equal(saved["turn_command"],s["turn_command"])
        np.testing.assert_array_equal(saved["escape_event"],d.escape_event)
    with pytest.raises(FileExistsError): module.save_action(tmp_path/"actions","sample",d,s,action,{})
    with pytest.raises(ValueError): module.save_action(ROOT/"connectome/phase7/results","blocked",d,s,action,{})
