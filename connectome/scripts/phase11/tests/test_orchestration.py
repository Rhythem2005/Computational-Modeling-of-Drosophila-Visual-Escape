"""Engineering fixtures; never full benchmark fits or scientific freezes."""
from copy import deepcopy
import json
import numpy as np
import pytest
from connectome.scripts.phase10.gru import train_run, GRU
from connectome.scripts.phase11.training import train_trial, restore
from connectome.scripts.phase11.common import OUT, read, write, sha, digest
from connectome.scripts.phase11.assessment import assess, behavior
from connectome.scripts.phase8.decoder import decode_score, Threshold


@pytest.fixture(autouse=True)
def unique_output_root(monkeypatch, tmp_path):
    import sys
    import uuid
    from connectome.scripts.phase11 import dataset
    root = OUT/'test_artifacts'/uuid.uuid4().hex
    monkeypatch.setattr(sys.modules[__name__], 'OUT', root)
    monkeypatch.setattr(dataset, 'OUT', root)


def samples():
    rng = np.random.default_rng(411)
    from connectome.scripts.phase6.encoder import load_mapping
    dn = np.array(load_mapping()['channel_index']) < 0
    sets = []
    for split in ('train', 'validation'):
        rows = []
        for k in range(20):
            x = rng.uniform(0, .1, (24, 321))
            x[:, dn] = 0.
            rows.append(dict(scenario_id=f'fixture_{split}_{k}', group_id=f'fixture_{split}_{k}',
                  split=split, cohort=split, role='looming' if k%2 else 'static_initial', label=k%2, inputs=x))
        sets.append(rows)
    return sets


@pytest.mark.parametrize('pause', [1, 2, 3, 4])
def test_resume_mid_batch_and_epoch_exactly_matches_frozen_training(tmp_path, pause):
    train, val = samples()
    # Use unique directories under the Phase 11 output guard, isolated per test.
    base = OUT/'tests'/tmp_path.name
    expected, reference = train_run(train, val, 55100, .001, smoke=True, smoke_epochs=3, smoke_start=8)
    initial, report = train_trial(train, val, 55100, .001, base, {'mapping': 'synthetic_fixture'},
                                  smoke=True, smoke_epochs=3, pause_after_updates=pause)
    assert initial is None and report['status'] == 'PAUSED_CHECKPOINT'
    current = read(base/'current.json')
    assert current['adam_updates'] == pause
    actual, result = train_trial(train, val, 55100, .001, base, {'mapping': 'synthetic_fixture'}, smoke=True, smoke_epochs=3)
    assert result['history'] == reference['history']
    assert result['best_epoch'] == reference['best_epoch']
    for k in expected.p:
        np.testing.assert_array_equal(actual.p[k], expected.p[k])
    again, complete = train_trial(train, val, 55100, .001, base, {'mapping': 'synthetic_fixture'}, smoke=True, smoke_epochs=3)
    assert complete['history'] == result['history']
    for k in actual.p:
        np.testing.assert_array_equal(again.p[k], actual.p[k])


def test_checkpoint_tamper_and_identity_rejected(tmp_path):
    train, val = samples()
    base = OUT/'tests'/tmp_path.name
    train_trial(train, val, 55100, .0003, base, {'mapping': 'fixture'}, smoke=True, pause_after_updates=1)
    current = read(base/'current.json')
    with pytest.raises(ValueError, match='contract'):
        train_trial(train, val, 55100, .001, base, {'mapping': 'fixture'}, smoke=True)
    path = base/current['arrays_file']
    path.write_bytes(path.read_bytes()+b'tamper')
    with pytest.raises(ValueError, match='hash'):
        restore(base, current['contract'])


def test_uncommitted_array_generation_is_ignored(tmp_path):
    train, val = samples()
    base = OUT/'tests'/tmp_path.name
    train_trial(train, val, 55100, .001, base, {'mapping': 'fixture'}, smoke=True, pause_after_updates=1)
    (base/'state_000002.npz').write_bytes(b'interrupted uncommitted write')
    _, result = train_trial(train, val, 55100, .001, base, {'mapping': 'fixture'}, smoke=True)
    assert result['epochs_run'] == 2 and result['updates'] == 4


def test_no_validation_gradient_and_early_stop_restores_patience(tmp_path, monkeypatch):
    train, val = samples()
    original = GRU.loss
    def loss(self, x, y, window_start=200, gradient=False):
        return original(self, x, y, window_start, gradient) if gradient else 1.
    monkeypatch.setattr(GRU, 'loss', loss)
    base = OUT/'tests'/tmp_path.name
    train_trial(train, val, 55100, .001, base, {'mapping': 'fixture'}, smoke=True, smoke_epochs=30, pause_after_updates=4)
    net, report = train_trial(train, val, 55100, .001, base, {'mapping': 'fixture'}, smoke=True, smoke_epochs=30)
    assert report['epochs_run'] == 21 and report['best_epoch'] == 1


def test_production_rejects_smoke_and_test_before_training(tmp_path):
    train, val = samples()
    with pytest.raises(ValueError):
        train_trial(train, val, 55100, .001, OUT/'tests'/tmp_path.name, {'mapping': 'fixture'})
    val[0]['split'] = 'test'
    with pytest.raises(ValueError):
        train_trial(train, val, 55100, .001, OUT/'tests'/tmp_path.name, {'mapping': 'fixture'}, smoke=True)


def score_sets():
    identity = dict(model_id='fixture')
    sets = []
    for split in ('train', 'validation'):
        rows = []
        for k, role in enumerate(('looming', 'static_initial', 'static_terminal', 'translating_initial')):
            score = np.zeros(1000)
            score[200:] = .3 if k == 0 else 0.
            rows.append(dict(scenario_id=f'{split}_{role}', group_id=split, split=split, cohort=split,
                   role=role, label=int(k == 0), score=score, identity=identity))
        sets.append(rows)
    return identity, *sets


def test_subnormal_json_reload_comparison_and_inference(tmp_path):
    value = float(np.nextafter(0., np.inf))
    assert np.array(value).view(np.uint64).item() == 1
    path = OUT/'tests'/tmp_path.name/'subnormal.json'
    write(path, dict(kind='finite', value=value))
    threshold = Threshold(**read(path))
    assert threshold.value == 5e-324 and threshold.value > 0
    assert not (0. >= threshold.value)
    times = np.arange(1000, dtype=np.float64)
    silent = decode_score(times, np.zeros(1000), 1000., threshold)
    exact = decode_score(times, np.full(1000, value), 1000., threshold)
    assert silent.first_event_ms is None and exact.first_event_ms == 20.
    identity, train, val = score_sets()
    report = assess(train, val, identity, smoke=True)
    assert report['threshold'] == read(path)
    assert report['behavior']['validation']['timely_tpr'] == 1


def test_no_feasible_finite_threshold_uses_declared_sentinel():
    identity, train, val = score_sets()
    for r in val:
        r['score'][:] = .3
    report = assess(train, val, identity, smoke=True)
    assert report['feasibility']['no_eligible_finite_threshold']
    assert not report['feasibility']['no_eligible_threshold']
    assert report['threshold']['kind'] == 'always_silent'
    assert report['feasibility']['rule_relaxed'] is False


def test_behavior_retains_early_missed_and_end_boundary():
    _, train, _ = score_sets()
    threshold = dict(kind='finite', value=.1)
    train[0]['score'][:] = .3
    early = behavior(train, threshold)
    assert early['early_positive_alarms'] == 1 and early['timely_tpr'] == 0
    train[0]['score'][:] = 0.
    train[0]['score'][980:] = .3
    end = behavior(train, threshold)
    assert end['missed_positives'] == 1
    train[0]['score'][979:] = .3
    assert behavior(train, threshold)['per_episode'][0]['first_event_ms'] == 999.


@pytest.mark.parametrize('mapping', ['uniform_population', 55010, 55011, 55012, 55013, 55014])
def test_phase11_dataset_denies_held_out_before_any_load(mapping):
    from connectome.scripts.phase11.dataset import Dataset
    obj = object.__new__(Dataset)
    obj.rows = {'test_example': dict(split='test', cohort='test_id')}
    with pytest.raises(ValueError, match='forbidden'):
        obj.load('test_example')


def test_registered_schedule_keeps_every_seed_gain_and_mapping():
    from collections import Counter
    from connectome.scripts.phase11.jobs import schedule
    rows = schedule()
    assert len(rows) == len({r['job_id'] for r in rows}) == 936
    assert Counter(r['kind'] for r in rows) == {'gru_trial': 120, 'calibration': 816}
    assert set(r['mapping'] for r in rows) == {'uniform_population', 55010, 55011, 55012, 55013, 55014}
    assert all(sum(r['mapping'] == mapping and r['kind'] == 'calibration' for r in rows) == 136
               for mapping in {'uniform_population', 55010, 55011, 55012, 55013, 55014})


@pytest.mark.parametrize('mapping', ['uniform_population', 55010, 55011, 55012, 55013, 55014])
def test_frame_cache_matches_frozen_encoder_and_rejects_tamper(mapping):
    from connectome.scripts.phase11.dataset import Dataset
    from connectome.scripts.phase7.pipeline import FrozenPipeline
    pipeline = FrozenPipeline()
    data = Dataset(pipeline, mapping)
    sid = 'train_f0000_looming'
    data.rows = {sid: data.rows[sid]}
    identity = data.prepare()
    assert identity['clips'] == 1
    held = data.load(sid)
    raw, _, _ = data.frame_arrays(sid)
    np.testing.assert_array_equal(held[16], raw[0])
    np.testing.assert_array_equal(held[17], raw[1])
    assert 0 <= data.index[sid]['valid_frame_fraction'] <= 1
    data.frame_arrays.cache_clear()
    path = data.directory/f'{sid}.npz'
    path.write_bytes(path.read_bytes()+b'tamper')
    with pytest.raises(ValueError, match='tampered'):
        data.prepare()


def test_atomic_publication_commits_arrays_before_pointer(tmp_path):
    from connectome.scripts.phase11.launch import publish
    from connectome.scripts.phase11.common import arrays
    source, dest = OUT/'publish_source', OUT/'publish_dest'
    path = source/'trial/state_000001.npz'
    arrays(path, x=np.array([1.]))
    metadata = dict(arrays_file=path.name, arrays_sha256=sha(path), generation=1)
    write(path.parent/'current.json', metadata)
    publish(source, dest)
    current = read(dest/'trial/current.json')
    assert sha(dest/'trial'/current['arrays_file']) == current['arrays_sha256']
    # An orphan (uncommitted) next generation cannot replace the pointer.
    arrays(source/'trial/state_000002.npz', x=np.array([2.]))
    publish(source, dest)
    assert read(dest/'trial/current.json')['generation'] == 1


def test_freeze_cannot_accept_smoke_or_untrained_gru():
    from connectome.scripts.phase11.jobs import freeze
    path = OUT/'freeze_model.json'
    write(path, dict(status='UNTRAINED'))
    calibration = dict(smoke_only=True, test_ids_used=[], identity=dict(model_id='gru', model_sha256=sha(path)))
    with pytest.raises(ValueError, match='Smoke'):
        freeze(OUT/'freeze.json', calibration, [path], {})
    calibration['smoke_only'] = False
    with pytest.raises(ValueError, match='training proof'):
        freeze(OUT/'freeze.json', calibration, [path], {})
