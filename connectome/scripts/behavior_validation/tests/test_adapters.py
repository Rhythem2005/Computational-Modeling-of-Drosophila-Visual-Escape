"""Development-trace checks only; no new behavioral conditions or held-out clips."""
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from connectome.scripts.phase7.pipeline import FrozenPipeline
from connectome.scripts.phase8.decoder import Threshold, StreamingDecoder, decode_score
from connectome.scripts.phase9.config import load_config, fixtures
from connectome.scripts.phase9.world import World, render_camera, swept_contact
from connectome.scripts.phase10.models import score_model
from connectome.scripts.behavior_validation.common import ROOT
from connectome.scripts.behavior_validation.artifacts import load_roster
from connectome.scripts.behavior_validation.controllers import Controller
from connectome.scripts.behavior_validation.evidence import load_episode

@pytest.fixture(scope='session')
def pipeline():
    return FrozenPipeline()

@pytest.fixture(scope='session')
def roster(pipeline):
    return load_roster(pipeline)

def trace(mapping='uniform_population'):
    name='world_head_on_primary' if mapping=='uniform_population' else 'world_left_spatial_s55010'
    with np.load(ROOT/f'connectome/phase9/results/episodes/{name}.npz',allow_pickle=False) as f:
        return {k:f[k].copy() for k in f.files}

def replay(row,pipeline,drive):
    c=Controller(row['model'],pipeline,row.get('net'))
    scores=[];states=[c.state_vector()]
    for d in drive:
        scores.append(c.score(d));c.advance(d);states.append(c.state_vector())
    return np.array(scores), np.array(states)

@pytest.mark.parametrize('mapping',['uniform_population','55010'])
def test_roster_and_control_contracts(roster,mapping):
    rows=roster[mapping]
    assert len(rows)==13
    assert [r['seed'] for r in rows if r['model']=='gru']==list(range(55100,55110))
    assert rows[2]['threshold']==dict(kind='always_silent',value=None)

@pytest.mark.parametrize('mapping',['uniform_population','55010'])
@pytest.mark.parametrize('index',range(10))
def test_gru_streaming_exact_batch_and_reset(pipeline,roster,mapping,index):
    row=roster[mapping][index+3]
    drive=trace(mapping)['step_drive_unscaled']
    actual, states=replay(row,pipeline,drive)
    logits,cache=row['net'].forward(.4*drive[None],cache=True)
    from connectome.scripts.phase10.gru import sigmoid
    np.testing.assert_array_equal(actual,sigmoid(logits)[0])
    np.testing.assert_array_equal(states,cache[1][0])
    # Reset order independence and causal prefix on the same approved input trace.
    c=Controller('gru',pipeline,row['net']);c.advance(drive[250]);c.reset()
    assert c.score(drive[0])==actual[0]
    prefix,_=replay(row,pipeline,drive[:40])
    np.testing.assert_array_equal(prefix,actual[:40])
    decoded=decode_score(np.arange(len(actual),dtype=np.float64),actual,1000.,Threshold(**row['threshold']))
    stream=StreamingDecoder(Threshold(**row['threshold']),1000)
    for k,score in enumerate(actual):
        out=stream.update(float(k),float(score))
        for key in ('sustained_score','eligible','escape_event','escape_requested'):
            assert out[key]==getattr(decoded,key)[k]

@pytest.mark.parametrize('mapping',['uniform_population','55010'])
def test_circuit_feature_and_no_action_saved_drive(pipeline,roster,mapping):
    saved=trace(mapping);drive=saved['step_drive_unscaled']
    score,states=replay(roster[mapping][0],pipeline,drive)
    np.testing.assert_array_equal(score,saved['score'])
    np.testing.assert_array_equal(states,saved['states'])
    score,_=replay(roster[mapping][1],pipeline,drive)
    np.testing.assert_array_equal(score,score_model('feature_only',drive,pipeline))
    score,_=replay(roster[mapping][2],pipeline,drive)
    assert not score.any()

def test_input_validation_and_model_rejection(pipeline,roster):
    with pytest.raises(ValueError):Controller('unknown',pipeline)
    with pytest.raises(ValueError):Controller('gru',pipeline)
    c=Controller('circuit',pipeline)
    d=np.zeros(321);d[c.assigned<0]=1
    with pytest.raises(ValueError):c.score(d)
    with pytest.raises(ValueError):c.score(np.zeros(321,dtype=np.float32))
    with pytest.raises(ValueError):c.score(np.full(321,np.nan))

def test_decoder_boundaries_and_latch(roster):
    finite=roster['uniform_population'][0]['threshold']
    stream=StreamingDecoder(Threshold(**finite),1000)
    events=[]
    for k in range(1000):
        events.append(stream.update(float(k),1.)['escape_event'])
    assert np.flatnonzero(events).tolist()==[20]
    with pytest.raises(ValueError):stream.update(1000.,1.)
    silent=StreamingDecoder(Threshold('always_silent',None),1000)
    assert not any(silent.update(float(k),1.)['escape_event'] for k in range(1000))

def test_frame_availability_and_future_prefix(pipeline):
    saved=trace();frames=saved['frames'];times=saved['frame_timestamps_s']
    assert np.searchsorted(times,.016,side='right')-1==0
    assert np.searchsorted(times,.017,side='right')-1==1
    original=pipeline.encoder.encode(frames[:20],times[:20])
    changed=frames.copy();changed[20:]=128
    encoded=pipeline.encoder.encode(changed,times)
    np.testing.assert_array_equal(original.drive,encoded.drive[:20])

def test_world_delay_latch_and_existing_collision():
    config=load_config();s=fixtures()[0]
    world=World(config,s)
    assert world.request(0.)
    assert not world.request(1.)
    for _ in range(21):world.step()
    assert world.first_motion_ms is None
    world.step()
    assert world.first_motion_ms==21.
    assert world.turn==0 and world.activate_ms==20
    # Existing head-on geometry: analytic stationary contact, no extra episode.
    hit,_=swept_contact(np.array([0.,20.]),np.array([0.,-20.]),2.)
    assert 200+hit*800==920.

def test_stored_metric_checker_and_hash_rejection(tmp_path):
    # The checker is exercised against scheduled runs by the executor; malformed
    # metadata must fail before accepting a saved trajectory.
    (tmp_path/'bad.json').write_text('{"protocol":"wrong","arrays_sha256":"bad"}')
    with pytest.raises(ValueError):load_episode(tmp_path,'bad')

def test_no_training_dispatch_during_loading(pipeline,monkeypatch):
    from connectome.scripts.phase11 import training,jobs
    from connectome.scripts.phase10.gru import GRU
    def forbidden(*args,**kwargs):raise AssertionError('Training/inference during artifact load forbidden')
    monkeypatch.setattr(training,'train_trial',forbidden)
    monkeypatch.setattr(jobs,'train_trial',forbidden)
    monkeypatch.setattr(GRU,'forward',forbidden)
    result=load_roster(pipeline)
    assert len(result['uniform_population'])==13
