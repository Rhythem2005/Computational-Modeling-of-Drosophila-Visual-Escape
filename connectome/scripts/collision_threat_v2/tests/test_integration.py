"""Replay a saved pre-action prefix to check complete drivers, not world outcomes."""
import numpy as np
import pytest
import yaml
from connectome.scripts.collision_threat_v2.common import ROOT,REFERENCE
from connectome.scripts.collision_threat_v2.driver import Driver,ROLES
from connectome.scripts.collision_threat_v2.rule import KnownSizePrior
from connectome.scripts.collision_threat_v1.features import camera_from_config
from connectome.scripts.collision_threat_v1.protocol import legacy_rows
from connectome.scripts.phase7.pipeline import FrozenPipeline
from connectome.scripts.phase9.config import load_config

@pytest.fixture(scope='module')
def setup():
    pipeline=FrozenPipeline()
    camera=camera_from_config(load_config(),yaml.safe_load((ROOT/'connectome/phase6/encoder_config.yaml').read_text()))
    return pipeline,camera,legacy_rows(pipeline)

@pytest.mark.parametrize('model',list(ROLES))
def test_saved_prefix_driver_timing_and_metadata(setup,model):
    pipeline,camera,rows=setup
    driver=Driver(model,pipeline,camera,rows,KnownSizePrior(1.5,.5))
    name='world_head_on_no_action_r0.npz'
    with np.load(REFERENCE/'episodes'/name,allow_pickle=False) as f:
        frames=f['frames'];times=f['frame_timestamps_s'];drive=f['decision_drive_unscaled'][:240]
    processed=0;events=[]
    for k,d in enumerate(drive):
        available=int(np.searchsorted(times,k/1000,side='right'))
        for j in range(processed,available):driver.observe(frames[j],times[j])
        processed=available
        out=driver.sample(k,d)
        assert all(key in out for key in ('gate_state','candidate_epoch','retirement_event','rearm_event',
                   'unknown_after_retirement','legacy_escape_event','escape_event','physical_reason'))
        if out['escape_event']:events.append(k)
        driver.advance(d)
    expected=[] if model=='no_action' else [237] if 'standalone' in model else [239]
    assert events==expected
    assert driver.physical_request_ms==(None if not expected else expected[0])
