"""Saved-artifact freeze replay and strict metadata-only source compatibility."""
import json
import shutil
import uuid
import pytest
from connectome.scripts.phase11.common import ROOT,OUT,read,write,sha
from connectome.scripts.phase11.jobs import freeze,verify_freeze


def saved_artifacts():
    folder=OUT/'calibration/cal_uniform_population_gru_55100'
    selected=OUT/'selected/uniform_population/gru_55100.npz'
    return folder,selected,[selected,selected.with_suffix('.json'),OUT/'inputs/uniform_population/index.json',
                            folder/'assessments.json',folder/'diagnostics.json']


def test_real_failed_freeze_replays_with_list_diagnostics():
    folder,selected,artifacts=saved_artifacts()
    assert isinstance(read(folder/'diagnostics.json'),list)
    assert read(selected.with_suffix('.json'))['status']=='TRAIN_VALIDATION_SELECTED'
    before={str(p):sha(p) for p in artifacts}
    path=OUT/'tests/calibration_repair'/uuid.uuid4().hex/'freeze.json'
    calibration=read(folder/'assessments.json')
    freeze(path,calibration,artifacts,read(OUT/'training/train_uniform_population_55100_0p0003/current.json')['contract']['input_identity'])
    assert verify_freeze(path)['calibration']==calibration
    assert {str(p):sha(p) for p in artifacts}==before


def test_list_diagnostics_cannot_replace_selected_training_proof():
    folder,selected,artifacts=saved_artifacts()
    artifacts.remove(selected.with_suffix('.json'))
    with pytest.raises(ValueError,match='training proof'):
        freeze(OUT/'tests/calibration_repair'/uuid.uuid4().hex/'freeze.json',read(folder/'assessments.json'),artifacts,{})


def test_ambiguous_selected_proofs_still_rejected():
    folder,selected,artifacts=saved_artifacts()
    duplicate=OUT/'tests/calibration_repair'/uuid.uuid4().hex/'duplicate.json'
    write(duplicate,read(selected.with_suffix('.json')))
    with pytest.raises(ValueError,match='training proof'):
        freeze(duplicate.parent/'freeze.json',read(folder/'assessments.json'),artifacts+[duplicate],{})


@pytest.fixture
def compatibility(monkeypatch):
    from connectome.scripts.phase11 import repair_provenance as module
    directory=OUT/'tests/calibration_repair'/uuid.uuid4().hex
    artifact=directory/'old_artifact.json';write(artifact,dict(unit_only=True))
    old={'unit/jobs.py':'old','unit/training.py':'same'}
    current={'unit/jobs.py':'new','unit/training.py':'same','unit/repair.py':'added'}
    certificate=dict(legacy_sources_sha256=old,approved_changed_existing_sources={'unit/jobs.py':'new'},
                     frozen_bindings_sha256={},legacy_artifacts_sha256={str(artifact.relative_to(ROOT)):sha(artifact)})
    write(directory/'compatibility_certificate.json',certificate)
    digest=sha(directory/'compatibility_certificate.json')
    write(directory/'approval.json',dict(status='APPROVED_POST_TESTS',certificate_sha256=digest,new_sources_sha256=current))
    monkeypatch.setattr(module,'REPAIR',directory)
    monkeypatch.setattr(module,'CERTIFICATE_SHA256',digest)
    monkeypatch.setattr(module,'sources',lambda:current)
    return module,directory,artifact,old,current


def test_exact_legacy_artifact_and_source_pair_accepted(compatibility):
    module,_,artifact,old,_=compatibility
    module.require_compatible_sources(old,artifact)


@pytest.mark.parametrize('fault',['artifact','unbound','legacy_sources','current_sources','approval','certificate'])
def test_compatibility_rejects_unapproved_changes(compatibility,fault):
    module,directory,artifact,old,current=compatibility
    if fault=='artifact':write(artifact,dict(changed=True))
    if fault=='unbound':artifact=directory/'other.json';write(artifact,dict(unit_only=True))
    if fault=='legacy_sources':old=dict(old,other='unregistered')
    if fault=='current_sources':current['unit/training.py']='changed'
    if fault=='approval':
        approval=read(directory/'approval.json');approval['status']='CANDIDATE_NOT_APPROVED';write(directory/'approval.json',approval)
    if fault=='certificate':write(directory/'compatibility_certificate.json',dict(changed=True))
    with pytest.raises(ValueError):module.require_compatible_sources(old,artifact)
