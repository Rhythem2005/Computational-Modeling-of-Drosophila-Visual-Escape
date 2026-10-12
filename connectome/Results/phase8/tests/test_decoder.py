from copy import deepcopy
import json

import numpy as np
import pytest

from connectome.scripts.phase6.encoder import load_mapping
from connectome.scripts.phase8.decoder import (Threshold, StreamingDecoder, decode_score, InitiationDecoder,
                                             sustained_negative_max, load_config)
from connectome.scripts.phase8.candidates import build_candidates, rank_validation_assessments, finalize_primary_calibration
from connectome.scripts.phase8 import activity_io
from connectome.scripts.phase8.evidence import ROOT


def trace(score, threshold=0.5, duration=None):
    score = np.array(score, dtype=np.float64)
    return decode_score(np.arange(len(score), dtype=np.float64), score,
                        float(len(score) if duration is None else duration), Threshold("finite", threshold))


def brute(score, threshold):
    # Independent 21-value slice reference: 20 elapsed intervals.
    minima = np.zeros(len(score), dtype=np.float64)
    for k in range(20, len(score)):
        minima[k] = min(score[k - 20:k + 1])
    indices = np.flatnonzero((np.arange(len(score)) >= 20) & (minima >= threshold))
    return minima, None if len(indices) == 0 else float(indices[0])


@pytest.mark.parametrize("length", [1, 19, 20, 21, 30, 1000])
def test_exact_elapsed_persistence_and_eligibility(length):
    out = trace(np.ones(length))
    assert out.first_event_ms == (20.0 if length >= 21 else None)
    assert out.escape_event.sum() == (1 if length >= 21 else 0)
    assert np.all(~out.eligible[:20])


@pytest.mark.parametrize("seed", [0, 1, 2, 17, 99])
def test_streaming_reference_exact_and_bounded_history(seed):
    rng = np.random.default_rng(seed)
    score = rng.choice([0, 0.4, 0.5, 0.7, 1.0], size=1000).astype(np.float64)
    score[211:260] = 0.5
    out = trace(score)
    minima, event = brute(score, 0.5)
    np.testing.assert_array_equal(out.sustained_score, minima)
    assert out.first_event_ms == event
    stream = StreamingDecoder(Threshold("finite", 0.5), 1000.0)
    for k, value in enumerate(score):
        stream.update(float(k), float(value))
        assert len(stream.history) <= 21


def test_19ms_pulse_fails_20ms_passes():
    too_short = np.zeros(100)
    too_short[10:30] = 1.0  # elapsed 19 ms between first and last high sample
    assert trace(too_short).first_event_ms is None
    full = np.zeros(100)
    full[10:31] = 1.0
    assert trace(full).first_event_ms == 30.0


def test_current_drop_cancels_and_threshold_equality_counts():
    signal = np.ones(50) * 0.5
    signal[20] = np.nextafter(0.5, -np.inf)
    assert trace(signal).first_event_ms == 41.0
    assert trace(np.ones(30) * 0.5).first_event_ms == 20.0


def test_first_event_latched_even_after_drop_and_pre_onset():
    signal = np.zeros(1000)
    signal[10:40] = 1.0
    signal[400:700] = 2.0
    out = trace(signal)
    assert out.first_event_ms == 30.0 and out.escape_event.sum() == 1
    assert np.all(out.escape_requested[30:]) and np.all(~out.escape_requested[:30])
    assert out.action()["steering"] is None


@pytest.mark.parametrize("cut", [1, 20, 21, 231, 500])
def test_prefix_and_future_invariance(cut):
    signal = np.zeros(1000)
    signal[211:] = 1.0
    original = trace(signal)
    altered = signal.copy()
    altered[cut:] = 10.0
    changed = trace(altered)
    prefix = trace(signal[:cut], duration=1000.0)
    for key in ("score", "sustained_score", "eligible", "escape_event", "escape_requested"):
        np.testing.assert_array_equal(getattr(original, key)[:cut], getattr(changed, key)[:cut])
        np.testing.assert_array_equal(getattr(original, key)[:cut], getattr(prefix, key))


def test_sentinel_is_silent_without_infinity():
    signal = np.ones(100) * 1e200
    out = decode_score(np.arange(100, dtype=np.float64), signal, 100.0, Threshold("always_silent", None))
    assert out.first_event_ms is None and not out.escape_event.any() and not out.escape_requested.any()
    assert json.loads(json.dumps(out.action(), allow_nan=False))["threshold"]["value"] is None


@pytest.mark.parametrize("kind,value", [("invalid", 1), ("finite", None), ("finite", True), ("finite", -1), ("finite", np.nan), ("finite", np.inf), ("always_silent", 1)])
def test_invalid_threshold_rejected(kind, value):
    with pytest.raises(ValueError): Threshold(kind, value)


@pytest.mark.parametrize("fault", ["time_dtype", "score_dtype", "nan", "negative", "length", "gap", "offset", "endpoint", "duration", "final_status"])
def test_invalid_series_rejected(fault):
    times = np.arange(50, dtype=np.float64)
    score = np.ones(50, dtype=np.float64)
    duration = 50.0
    status = "synthetic_fixture"
    if fault == "time_dtype": times = times.astype(np.float32)
    elif fault == "score_dtype": score = score.astype(np.float32)
    elif fault == "nan": score[4] = np.nan
    elif fault == "negative": score[4] = -1
    elif fault == "length": score = score[:-1]
    elif fault == "gap": times[4] += 0.5
    elif fault == "offset": times += 1
    elif fault == "endpoint": duration = 49.0
    elif fault == "duration": duration = 49.5
    elif fault == "final_status": status = "final_calibrated"
    with pytest.raises(ValueError): decode_score(times, score, duration, Threshold("finite", 0.5), threshold_status=status)


def states_fixture():
    ids = np.array(load_mapping()["body_ids"], dtype=np.int64)
    times = np.arange(1001, dtype=np.float64)
    states = np.zeros((1001, 321), dtype=np.float64)
    return times, states, ids


def test_only_bilateral_primary_mean_drives_action():
    times, states, ids = states_fixture()
    decoder = InitiationDecoder(Threshold("finite", 0.5))
    states[:, ids == 10010] = 1.0
    states[:, ids == 10001] = 0.0
    out = decoder.decode_activity(times, states, ids, 1000.0)
    assert np.all(out.score == 0.5) and out.first_event_ms == 20
    assert out.dn_activity.shape == (1000, 10) and out.dn_body_ids.shape == (10,)
    states[:, (ids != 10010) & (ids != 10001)] = 1e6
    again = decoder.decode_activity(times, states, ids, 1000.0)
    np.testing.assert_array_equal(out.escape_event, again.escape_event)
    np.testing.assert_array_equal(out.score, again.score)


@pytest.mark.parametrize("start,expected", [(979, 999.0), (980, None)])
def test_final_state_endpoint_excluded(start, expected):
    times, states, ids = states_fixture()
    states[start:, ids == 10010] = 1.0
    states[start:, ids == 10001] = 1.0
    out = InitiationDecoder(Threshold("finite", 0.5)).decode_activity(times, states, ids, 1000.0)
    assert len(out.times_ms) == 1000 and out.first_event_ms == expected


@pytest.mark.parametrize("fault", ["reorder", "missing", "id_dtype", "state_dtype", "negative", "inf", "time", "duration_none"])
def test_activity_contract_rejection(fault):
    times, states, ids = states_fixture()
    duration = 1000.0
    if fault == "reorder": ids = ids[::-1]
    elif fault == "missing": ids = ids[:-1]
    elif fault == "id_dtype": ids = ids.astype(float)
    elif fault == "state_dtype": states = states.astype(np.float32)
    elif fault == "negative": states[0, 0] = -1.0
    elif fault == "inf": states[0, 0] = np.inf
    elif fault == "time": times[3] += 0.5
    elif fault == "duration_none": duration = None
    with pytest.raises(ValueError): InitiationDecoder(Threshold("finite", 0.5)).decode_activity(times, states, ids, duration)


def records(values=(0.0, 0.0)):
    return [dict(scenario_id=f"train_f{k:04d}_static_initial", group_id=f"train_f{k:04d}", split="train", cohort="train",
                 label=0, role="static_initial", sustained_score_max=float(v)) for k, v in enumerate(values)]


def test_amendment_zero_quantiles_original_failure_audited():
    original = build_candidates(records(), policy="raw_quantile_original_v1")
    amended = build_candidates(records())
    assert original["unique_finite_candidates"] == amended["unique_finite_candidates"] == 1
    old = original["candidates"][0]["threshold"]["value"]
    new = amended["candidates"][0]["threshold"]["value"]
    assert old == 0 and new == np.nextafter(0.0, np.inf)
    assert trace(np.zeros(100), old).first_event_ms == 20.0
    assert trace(np.zeros(100), new).first_event_ms is None
    assert trace(np.ones(100), new).first_event_ms == 20.0
    assert len(amended["candidates"][0]["quantile_sources"]) == 31


def test_candidate_budget_order_and_training_only_provenance():
    plan = build_candidates(records(np.arange(200)))
    assert len(plan["candidates"]) == 32 and plan["training_negative_count"] == 200
    finite = plan["candidates"][:-1]
    assert all(c["threshold"]["value"] > c["quantile_sources"][0]["raw_quantile"] for c in finite)
    assert all(a["threshold"]["value"] < b["threshold"]["value"] for a, b in zip(finite, finite[1:]))
    assert plan["provisional_demo_candidate_id"] == finite[-1]["candidate_id"]


@pytest.mark.parametrize("fault", ["validation", "test", "positive", "role", "duplicate", "nan", "negative", "empty"])
def test_reject_leaking_or_invalid_training_candidates(fault):
    rows = records()
    if fault == "validation": rows[0]["split"] = rows[0]["cohort"] = "validation"
    elif fault == "test": rows[0]["split"] = "test"; rows[0]["cohort"] = "test_id"
    elif fault == "positive": rows[0]["label"] = 1
    elif fault == "role": rows[0]["role"] = "looming"
    elif fault == "duplicate": rows[1]["scenario_id"] = rows[0]["scenario_id"]
    elif fault == "nan": rows[0]["sustained_score_max"] = np.nan
    elif fault == "negative": rows[0]["sustained_score_max"] = -1
    elif fault == "empty": rows = []
    with pytest.raises(ValueError): build_candidates(rows)


def test_overflow_fails_not_silent_replacement():
    with pytest.raises(ValueError): build_candidates(records([np.finfo(np.float64).max]))


def assessment(candidate_id, value, tpr, fpr):
    return dict(candidate_id=candidate_id, threshold=Threshold("always_silent", None).as_dict() if value is None else Threshold("finite", value).as_dict(), timely_tpr=tpr, full_episode_fpr=fpr)


def test_validation_ranking_and_calibration_gate():
    rows = [assessment("unsafe", 1, 1, 0.06), assessment("a", 2, .8, .04),
            assessment("b", 3, .8, .03), assessment("c", 4, .8, .03), assessment("silent", None, 0, 0)]
    assert rank_validation_assessments(rows)["candidate_id"] == "c"
    assert rank_validation_assessments([assessment("zero", 0, 1, 1), assessment("silent", None, 0, 0)])["candidate_id"] == "silent"
    with pytest.raises(RuntimeError, match="controls"): finalize_primary_calibration()


def test_episode_too_short_for_candidate_statistics():
    with pytest.raises(ValueError): sustained_negative_max(np.arange(20, dtype=np.float64), np.zeros(20), 20.0)


def test_stream_failure_does_not_advance_clock():
    stream = StreamingDecoder(Threshold("finite", .5), 30.0)
    with pytest.raises(ValueError): stream.update(1.0, 1.0)
    with pytest.raises(ValueError): stream.update(0.0, np.nan)
    assert stream.index == 0
    assert not stream.update(0.0, .5)["escape_event"]


def test_earlier_saved_activity_real_decoder_roundtrip(tmp_path, monkeypatch):
    times, states, ids, duration, source = activity_io.load_activity(ROOT / "connectome/phase7/results/activity", "train_f0000_looming")
    out = InitiationDecoder(Threshold("finite", 1.0)).decode_activity(times, states, ids, duration)
    assert out.first_event_ms is not None and out.escape_event.sum() == 1
    monkeypatch.setattr(activity_io, "PHASE", tmp_path)
    paths = activity_io.save_decoded(tmp_path / "decoded", "sample", out, source)
    with np.load(paths[0], allow_pickle=False) as data:
        for key in ("times_ms", "score", "sustained_score", "eligible", "escape_event", "escape_requested", "dn_body_ids", "dn_activity"):
            np.testing.assert_array_equal(data[key], getattr(out, key))
    assert json.loads(paths[1].read_text())["first_event_ms"] == out.first_event_ms
    with pytest.raises(FileExistsError): activity_io.save_decoded(tmp_path / "decoded", "sample", out, source)
    with pytest.raises(ValueError): activity_io.save_decoded(ROOT / "connectome/phase7/results", "blocked", out, source)


def test_evaluator_metadata_never_enters_decoder():
    times, states, ids = states_fixture()
    with pytest.raises(TypeError): InitiationDecoder(Threshold("finite", .5)).decode_activity(times, states, ids, 1000.0, label=1)
    assert load_config()["steering"] == "unavailable_no_spatial_mapping"
