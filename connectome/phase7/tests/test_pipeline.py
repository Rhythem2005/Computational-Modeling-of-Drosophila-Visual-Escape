from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

import numpy as np
import pytest

from connectome.scripts.phase4 import simulator
from connectome.scripts.phase5.generator import generate_stimulus
from connectome.scripts.phase5.stimulus_io import save_stimulus
from connectome.scripts.phase6.encoder import causal_hold
from connectome.scripts.phase7.evidence import ROOT
from connectome.scripts.phase7.pipeline import FrozenPipeline, MillisecondInput, save_run


@pytest.fixture(scope="module")
def pipeline():
    return FrozenPipeline()


@pytest.fixture(scope="module")
def family():
    manifest = json.loads((ROOT / "connectome/phase5_5/results/benchmark_manifest.json").read_text())
    return [row for row in manifest["scenarios"] if row["group_id"] == "train_f0000"]


@pytest.fixture(scope="module")
def encoded(pipeline, family):
    frames, timestamps = generate_stimulus(family[0]["config"])
    return pipeline.encoder.encode(frames, timestamps)


def synthetic(pipeline, encoded, timestamps):
    channels = np.array([[0.2 + k * 0.1, 0.4] for k in range(len(timestamps))], dtype=np.float64)
    assigned = np.array(pipeline.encoder.mapping["channel_index"])
    drive = np.zeros((len(timestamps), 321), dtype=np.float64)
    drive[:, assigned >= 0] = channels[:, assigned[assigned >= 0]]
    return replace(encoded, channels=channels, drive=drive, timestamps_s=np.array(timestamps, dtype=np.float64))


def test_frozen_defaults_mapping_and_orientation(pipeline):
    c = pipeline.circuit
    assert c.n_neurons == 321 and len(c.edges_df) == 11557 and c.W_raw.sum() == 91023
    np.testing.assert_array_equal(c.body_ids, pipeline.encoder.mapping["body_ids"])
    assert not np.array_equal(c.body_ids, sorted(c.body_ids))
    assert c.W_raw[c.id_to_idx[531898], c.id_to_idx[81112]] == 172
    config = pipeline.simulation_config
    assert config["duration"] == 500 and config["dt"] == 1 and config["gain"] == 0.5 and config["input_scale"] == 0.4
    assert all(tau == 10 for tau in config["tau"].values())
    assert config["clip_max"] == 50 and config["noise_std"] == 0
    assert pipeline.normalization["scales"] == [8.632185525889524, 8.417362938348457]


def test_60hz_hold_and_endpoint(pipeline, encoded):
    adapter = MillisecondInput(encoded, pipeline.circuit, pipeline.encoder)
    times = np.arange(1000, dtype=np.float64)
    indices = adapter.frame_indices(times)
    np.testing.assert_array_equal(indices, np.array([max(k for k, t in enumerate(encoded.timestamps_s) if t <= ms / 1000) for ms in times]))
    np.testing.assert_array_equal(adapter.sample(times), causal_hold(encoded.drive, encoded.timestamps_s, times / 1000))
    assert indices[16] == 0 and indices[17] == 1 and indices[999] == 59
    run = pipeline.run_encoded(encoded, 1000.0)
    assert run.states.shape == (1001, 321) and run.step_input_scaled.shape == (1000, 321)
    assert run.times_ms[-1] == 1000 and run.step_times_ms[-1] == 999
    np.testing.assert_array_equal(run.step_input_scaled, 0.4 * run.step_drive_unscaled)


def test_fractional_irregular_delayed_and_single_frame(pipeline, encoded):
    for timestamps in ([0.0034, 0.01725, 0.0317], [0.0034]):
        value = synthetic(pipeline, encoded, timestamps)
        adapter = MillisecondInput(value, pipeline.circuit, pipeline.encoder)
        times = np.arange(50, dtype=np.float64)
        np.testing.assert_array_equal(adapter.sample(times), causal_hold(value.drive, value.timestamps_s, times / 1000))
        assert np.all(adapter(3, 321) == 0)
        np.testing.assert_array_equal(adapter(4, 321), value.drive[0])
        np.testing.assert_array_equal(adapter(100, 321), value.drive[-1])
        assert pipeline.run_encoded(value, 50.0).states.shape == (51, 321)


def test_no_early_epsilon_and_exact_boundary(pipeline, encoded):
    # Choose an exactly representable 125 ms boundary to check strict availability.
    value = synthetic(pipeline, encoded, [0.125, 0.25])
    adapter = MillisecondInput(value, pipeline.circuit, pipeline.encoder)
    assert adapter.frame_indices([np.nextafter(125.0, -np.inf), 125.0, np.nextafter(125.0, np.inf)]).tolist() == [-1, 0, 0]
    assert np.all(adapter(124, 321) == 0)
    np.testing.assert_array_equal(adapter(125, 321), value.drive[0])


def test_independent_euler_reference_scaling_and_state_time(pipeline, encoded):
    value = synthetic(pipeline, encoded, [0.0034, 0.0102])
    run = pipeline.run_encoded(value, 20.0)
    expected = np.zeros_like(run.states)
    for k in range(20):
        available = np.flatnonzero(value.timestamps_s <= k / 1000)
        u = np.zeros(321) if not len(available) else value.drive[available[-1]]
        activation = 0.5 * (pipeline.weights @ expected[k]) + 0.4 * u
        expected[k + 1] = expected[k] + 0.1 * (-expected[k] + np.clip(activation, 0, 50))
    np.testing.assert_array_equal(run.states, expected)
    assert np.all(run.states[:5] == 0) and np.max(run.states[5]) > 0
    dn = np.array(pipeline.encoder.mapping["channel_index"]) < 0
    assert np.all(run.states[5, dn] == 0) and np.max(run.states[6, dn]) > 0
    assert np.all(run.step_input_scaled[:, dn] == 0)


@pytest.mark.parametrize("role", ["looming", "static_initial", "static_terminal", "translating_initial"])
def test_end_to_end_controls_loader_and_frozen_replay(pipeline, family, tmp_path, role):
    row = next(row for row in family if row["role"] == role)
    frames, ts = generate_stimulus(row["config"])
    save_stimulus(tmp_path, row["config"], frames, ts)
    run = pipeline.run_saved(tmp_path, row["scenario_id"])
    frozen = pipeline.load_frozen_encoded(row["scenario_id"])
    np.testing.assert_array_equal(run.encoded.drive, frozen.drive)
    replay = pipeline.run_encoded(frozen, 1000.0)
    np.testing.assert_array_equal(run.states, replay.states)
    assert run.metrics["activation_clipped_fraction"] == 0
    if role == "looming":
        assert run.metrics["activity_max"] > 0
        assert np.all(run.states[run.times_ms <= 200] == 0)
    else:
        assert np.all(run.states == 0)


def test_metadata_extra_fields_do_not_affect_activity(pipeline, family, tmp_path):
    row = family[0]
    frames, ts = generate_stimulus(row["config"])
    save_stimulus(tmp_path, row["config"], frames, ts)
    before = pipeline.run_saved(tmp_path, row["scenario_id"])
    path = tmp_path / f"{row['scenario_id']}_metadata.json"
    metadata = json.loads(path.read_text())
    metadata.update(label=0, evaluator_role="static", future_target=123456)
    path.write_text(json.dumps(metadata))
    after = pipeline.run_saved(tmp_path, row["scenario_id"])
    np.testing.assert_array_equal(before.states, after.states)


@pytest.mark.parametrize("cut", [13, 25, 30, 50])
def test_future_frames_leave_prior_activity_unchanged(pipeline, family, cut):
    frames, ts = generate_stimulus(family[0]["config"])
    original = pipeline.run_frames(frames, ts, 1000.0)
    changed = frames.copy()
    changed[cut:] = 128
    altered = pipeline.run_frames(changed, ts, 1000.0)
    # Input at step start affects the next state; include state at availability.
    prior = original.times_ms / 1000 <= ts[cut]
    np.testing.assert_array_equal(original.states[prior], altered.states[prior])
    assert np.any(original.states[~prior] != altered.states[~prior])


@pytest.mark.parametrize("fault", ["reorder", "duplicate", "id_dtype", "width", "nan", "negative", "above_cap", "dn_drive", "broadcast", "channels", "version", "config", "normalization", "timestamps", "timestamp_dtype"])
def test_reject_invalid_encoded_contract(pipeline, encoded, fault):
    value = deepcopy(encoded)
    if fault == "reorder": value.body_ids = value.body_ids[::-1]
    elif fault == "duplicate": value.body_ids[1] = value.body_ids[0]
    elif fault == "id_dtype": value.body_ids = value.body_ids.astype(float)
    elif fault == "width": value.drive = value.drive[:, :-1]
    elif fault == "nan": value.drive[0, 0] = np.nan
    elif fault == "negative": value.drive[0, 0] = -0.1
    elif fault == "above_cap": value.drive[0, 0] = 1.1
    elif fault == "dn_drive": value.drive[:, 0] = 0.1
    elif fault == "broadcast": value.drive[:, pipeline.circuit.id_to_idx[81112]] = 0.123
    elif fault == "channels": value.channels = value.channels[:, :1]
    elif fault == "version": value.encoder_version = "invalid"
    elif fault == "config": value.config_sha256 = "invalid"
    elif fault == "normalization": value.normalization_sha256 = "invalid"
    elif fault == "timestamps": value.timestamps_s[1] = value.timestamps_s[0]
    elif fault == "timestamp_dtype": value.timestamps_s = value.timestamps_s.astype(np.float32)
    with pytest.raises(ValueError): pipeline.run_encoded(value, 1000.0)


@pytest.mark.parametrize("duration", [None, True, 0, -1, float("nan"), float("inf"), 999.5, 100])
def test_reject_invalid_or_truncating_duration(pipeline, encoded, duration):
    with pytest.raises(ValueError): pipeline.run_encoded(encoded, duration)


def test_endpoint_frame_rejected(pipeline, encoded):
    value = synthetic(pipeline, encoded, [0.0, 1.0])
    with pytest.raises(ValueError): pipeline.run_encoded(value, 1000.0)


def test_input_callback_validation_and_snapshot(pipeline, encoded):
    value = deepcopy(encoded)
    adapter = MillisecondInput(value, pipeline.circuit, pipeline.encoder)
    expected = adapter(900, 321)
    value.drive[:] = 0
    np.testing.assert_array_equal(adapter(900, 321), expected)
    with pytest.raises(ValueError): adapter(0, 320)
    with pytest.raises(ValueError): adapter(float("nan"), 321)
    with pytest.raises(ValueError): adapter.frame_indices([[0]])


def test_zero_contrast_end_to_end(pipeline, family):
    config = deepcopy(family[0]["config"])
    config["object_intensity"] = config["background_intensity"]
    frames, ts = generate_stimulus(config)
    assert np.all(pipeline.run_frames(frames, ts, 1000.0).states == 0)


def test_saving_cannot_overwrite_prior_phases(pipeline, encoded):
    run = pipeline.run_encoded(encoded, 1000.0)
    with pytest.raises(ValueError): save_run(ROOT / "connectome/phase6/results", "blocked", run)
    with pytest.raises(ValueError): save_run(ROOT / "connectome/phase7/results", "../blocked", run)
