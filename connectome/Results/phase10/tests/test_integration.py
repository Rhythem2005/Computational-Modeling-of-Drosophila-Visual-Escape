from copy import deepcopy
import json
import numpy as np
import pytest
from connectome.scripts.phase10.common import OUT,save_arrays,write_json,config
from connectome.scripts.phase10.data import TrainingDataset,step_drive,validate_coverage,manifest_rows,hold_spatial_drive,validate_drive
from connectome.scripts.phase10.models import rate_trace,minimal_features,score_model,freeze_identity
from connectome.scripts.phase10.networks import stability,load_network
from connectome.scripts.phase10.calibration import calibrate,save_freeze,load_freeze
from connectome.scripts.phase10.gru import GRU


@pytest.fixture(scope='module')
def pipeline():
    from connectome.scripts.phase7.pipeline import FrozenPipeline
    return FrozenPipeline()


def test_reference_exact_frozen_pipeline_replay_and_minimal_controls(pipeline):
    from connectome.scripts.phase8.completion.controls import features_from_encoded
    encoded=pipeline.load_frozen_encoded('train_f0000_looming');drive=step_drive(encoded,pipeline)
    old=pipeline.run_encoded(encoded,1000.);new=rate_trace(drive,pipeline,pipeline.weights,stability(pipeline.weights,'native'))
    np.testing.assert_array_equal(new['states'],old.states)
    np.testing.assert_array_equal(drive,old.step_drive_unscaled)
    assert drive[16,0]==old.step_drive_unscaled[16,0]
    _,feature,linear=features_from_encoded(encoded);a,b=minimal_features(drive,pipeline)
    np.testing.assert_array_equal(a,feature);np.testing.assert_array_equal(b,linear)
    assert new['diagnostics']['clipped_fraction']==old.metrics['activation_clipped_fraction']


def test_training_loader_rejects_test_before_file_access_and_checks_manifest():
    class NoAccess:
        def load_frozen_encoded(self,sid):raise AssertionError('Test data access attempted')
    loader=TrainingDataset(NoAccess())
    with pytest.raises(ValueError):loader.load('test_id_f0000_looming')
    with pytest.raises(ValueError):loader.records('test_id')
    assert loader.audit==[]
    train=[r.copy() for r in manifest_rows() if r['cohort']=='train'];validate_coverage(train,'train')
    train[0]['label']=0
    with pytest.raises(ValueError):validate_coverage(train,'train')
    with pytest.raises(ValueError):validate_coverage(train[:-1],'train')


def synthetic_records():
    identity=freeze_identity('fixture','fixture_hash','native','uniform_population');sets=[]
    for split in ('train','validation'):
        rows=[]
        for k,role in enumerate(('looming','static_initial','static_terminal','translating_initial')):
            score=np.zeros(1000);score[200:]=.3 if k==0 else 0.
            rows.append(dict(scenario_id=f'smoke_{split}_{role}',group_id=f'smoke_{split}',split=split,cohort=split,label=int(k==0),
                             role=role,score=score,identity=identity))
        sets.append(rows)
    return identity,*sets


def test_shared_calibration_silence_persistence_budget_and_no_test_freeze():
    identity,train,val=synthetic_records();a=calibrate(train,val,identity,smoke=True)
    assert a['threshold']['value']==np.nextafter(0.,1.) and a['selected']['timely_tpr']==1.
    assert len(a['candidate_plan']['quantile_levels'])==31 and len(a['candidate_plan']['candidates'])<=32
    with pytest.raises(ValueError):save_freeze('smoke_forbidden',a,['none'])
    with pytest.raises(ValueError):calibrate(train,val,identity)
    val[0]['identity']=dict(identity,mapping=55010)
    with pytest.raises(ValueError):calibrate(train,val,identity,smoke=True)
    val[0]['identity']=identity;val[0]['cohort']='test_id'
    with pytest.raises(ValueError):calibrate(train,val,identity,smoke=True)


def test_calibration_keeps_early_event_and_silent_feasibility():
    identity,train,val=synthetic_records();val[0]['score'][:]=.3
    r=calibrate(train,val,identity,smoke=True)
    assert r['selected']['timely_tpr']==0 and r['threshold']['kind']=='always_silent'
    assert any(row['pre_onset_decisions'] for row in r['assessments'])


@pytest.mark.parametrize('seed',[55010,55011,55012,55013,55014])
def test_spatial_information_and_fractional_hold_are_shared(pipeline,seed):
    from connectome.scripts.phase8.completion.spatial import assign_fields,frame_drive
    t=np.arange(60,dtype=np.float64)/60;frames=np.full((60,256,256),128,dtype=np.uint8);y,x=np.indices((256,256))
    for k in range(60):frames[k][(x-90)**2+(y-128)**2<=(10+max(0,k-12)/3)**2]=64
    mapping=assign_fields(pipeline.encoder.mapping['nodes'],seed)
    encoded,raw,_=frame_drive(pipeline.encoder,frames,t,mapping)
    held=hold_spatial_drive(raw,t,encoded.body_ids,pipeline)
    np.testing.assert_array_equal(held[16],raw[0]);np.testing.assert_array_equal(held[17],raw[1])
    assert np.any(held>0) and np.all(held[:,np.array(pipeline.encoder.mapping['channel_index'])<0]==0)
    for model in ('circuit','population_average','weight_shuffle_00','degree_rewire_00','gru','feature_only'):
        score=score_model(model,held,pipeline,gru=GRU());assert score.shape==(1000,) and np.isfinite(score).all()
    with pytest.raises(ValueError):hold_spatial_drive(raw,t,encoded.body_ids[::-1],pipeline)


def test_invalid_drive_and_bank_tamper_cannot_be_used(pipeline):
    x=np.zeros((1000,321));x[0,0]=.1
    with pytest.raises(ValueError):validate_drive(x,pipeline)
    with pytest.raises(ValueError):validate_drive(np.zeros((999,321)),pipeline)
    with pytest.raises(ValueError):freeze_identity('a','b','native',55555)
    _,_,row=load_network('weight_shuffle_00',pipeline.circuit);path=OUT/row['path'];original=path.read_bytes();path.write_bytes(original+b'bad')
    try:
        with pytest.raises(ValueError):load_network('weight_shuffle_00',pipeline.circuit)
    finally:path.write_bytes(original)


def test_output_guard_immutable_definition_and_numerical_reproduction():
    p=OUT/'tests/roundtrip.npz';save_arrays(p,a=np.arange(4,dtype=np.float64));save_arrays(p,a=np.arange(4,dtype=np.float64))
    with pytest.raises(ValueError):save_arrays(p,a=np.arange(5,dtype=np.float64))
    with pytest.raises(ValueError):save_arrays(OUT.parent.parent/'phase9/bad.npz',a=np.zeros(1))
    write_json(OUT/'tests/immutable.json',{'a':1},immutable=True)
    with pytest.raises(ValueError):write_json(OUT/'tests/immutable.json',{'a':2},immutable=True)


def test_freeze_roundtrip_rejects_artifact_and_payload_tamper(monkeypatch):
    from connectome.scripts.phase10 import calibration as module
    from connectome.scripts.phase10.common import ROOT,sha
    sandbox=OUT/'tests/freeze_sandbox';sandbox.mkdir(parents=True,exist_ok=True)
    artifact=sandbox/'feature_model.json';write_json(artifact,dict(rule='same encoded mean; fixed .4 scale'),immutable=True)
    identity,train,val=synthetic_records();identity=dict(identity,model_id='feature_only',model_sha256=sha(artifact))
    for r in train+val:r['identity']=identity
    # A unit-only manifest stub exercises persistence without pretending to fit
    # real benchmark records. All artifacts stay under results/tests/.
    monkeypatch.setattr(module,'validate_coverage',lambda records,split:None)
    monkeypatch.setattr(module,'OUT',sandbox)
    result=module.calibrate(train,val,identity)
    saved=module.save_freeze('unit_only',result,[str(artifact.relative_to(ROOT))])
    loaded=module.load_freeze('unit_only');assert loaded['calibration']==saved['calibration']
    old=artifact.read_bytes();artifact.write_text('{}')
    try:
        with pytest.raises(ValueError):module.load_freeze('unit_only')
    finally:artifact.write_bytes(old)
    path=sandbox/'freezes/unit_only.json';old=path.read_bytes();path.write_text(path.read_text().replace('CALIBRATED_TRAIN_VALIDATION_ONLY','TAMPERED'))
    try:
        with pytest.raises(ValueError):module.load_freeze('unit_only')
    finally:path.write_bytes(old)


def test_untrained_gru_cannot_become_test_authorizing_freeze(monkeypatch):
    from connectome.scripts.phase10 import calibration as module
    from connectome.scripts.phase10.gru import save_gru
    from connectome.scripts.phase10.common import ROOT
    record=save_gru('unit_untrained',GRU(),dict(status='UNTRAINED',training=None))
    identity,train,val=synthetic_records();identity=dict(identity,model_id='gru',model_sha256=record['parameters_sha256'])
    for r in train+val:r['identity']=identity
    monkeypatch.setattr(module,'validate_coverage',lambda records,split:None)
    result=module.calibrate(train,val,identity)
    with pytest.raises(ValueError):module.save_freeze('unit_untrained',result,[str((OUT/'gru/unit_untrained.npz').relative_to(ROOT)),str((OUT/'gru/unit_untrained.json').relative_to(ROOT))])
