import json
from pathlib import Path
import numpy as np
import pytest
from dashboard.simulation.avoidance.contracts import verify_authorization,Settings
from dashboard.simulation.avoidance.recording import save_attempt

def test_protocol_approval_is_bound_to_exact_bytes(tmp_path):
    p=tmp_path/'protocol.json';p.write_text('{}');a=tmp_path/'approval.json'
    a.write_text(json.dumps(dict(status='APPROVED_EXACT_PROTOCOL',protocol_sha256='0'*64,episode_cap=24,training_authorized=False,held_out_authorized=False)))
    with pytest.raises(ValueError):verify_authorization(p,a)

def test_computed_arrays_survive_audit_failure(settings,tmp_path):
    from dashboard.simulation.avoidance.contracts import Scenario
    c=settings();s=Scenario('unit',(0,0,0),(0,0,0),({'id':'unit','position':[0,10,0],'velocity':[0,0,0],'radius':1.5,'onset_ms':0},))
    run=dict(arrays={'world_times_ms':np.array([0.,1.])},metrics={},commands=[])
    with pytest.raises(KeyError):save_attempt(tmp_path/'attempt',run,c,s)
    assert (tmp_path/'attempt/arrays.npz').exists()
    assert (tmp_path/'attempt/computed.json').exists()
    assert (tmp_path/'attempt/audit_failure.json').exists()
    assert not (tmp_path/'episodes/attempt.json').exists()

def test_new_physical_parameters_require_explicit_values(settings):
    from dataclasses import asdict
    d=asdict(settings());del d['association_gate_px']
    with pytest.raises(TypeError):Settings(**d)
