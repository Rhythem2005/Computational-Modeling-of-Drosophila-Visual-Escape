"""Frozen frame-to-activity pipeline. No action decoder or behavioral evaluation."""
from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
import time
import platform
import sys

import numpy as np
import yaml

from connectome.scripts.phase4 import loader, simulator
from connectome.scripts.phase5.loader import load_stimulus
from connectome.scripts.phase6.encoder import CausalEncoder, Encoded, VERSION, digest, load_config, validate_time
from .evidence import ROOT, PHASE, verify_frozen, file_hash, write_json

CONFIG_PATH = ROOT / "connectome/phase7/pipeline_config.yaml"
PIPELINE_VERSION = "1.0.0"


def load_pipeline_config():
    config = yaml.safe_load(CONFIG_PATH.read_text())
    expected = dict(pipeline_version=PIPELINE_VERSION, encoded_schema_version="1.0",
                    mapping="uniform_population", resampling="causal_zero_order_hold",
                    time_conversion="seconds_to_ms_explicit", initial_state="zeros", warmup_ms=0.0,
                    duration_source="explicit_episode_duration_ms",
                    simulation_config="connectome/phase4/simulation_config.yaml",
                    encoder_config="connectome/phase6/encoder_config.yaml",
                    normalization="connectome/phase6/results/normalization.json")
    if set(config) != set(expected) | {"validation_sample_ids"} or any(config[k] != v for k, v in expected.items()):
        raise ValueError("Unsupported Phase 7 pipeline configuration")
    ids = config["validation_sample_ids"]
    if not isinstance(ids, list) or len(ids) != len(set(ids)) or not all(isinstance(s, str) and s.startswith("train_") for s in ids):
        raise ValueError("Integration samples must be unique training scenarios")
    return config


class MillisecondInput:
    """Unscaled callback for Phase 4; seconds comparison has no early tolerance."""
    def __init__(self, encoded, circuit, encoder):
        ids = encoded.body_ids
        n = circuit.n_neurons
        if not isinstance(ids, np.ndarray) or ids.dtype != np.int64 or ids.shape != (n,) or not np.array_equal(ids, circuit.body_ids):
            raise ValueError("Encoded body IDs must match frozen simulator CSV order exactly")
        validate_time(encoded.timestamps_s, len(encoded.drive))
        if (not isinstance(encoded.drive, np.ndarray) or encoded.drive.dtype != np.float64 or
                encoded.drive.shape != (len(encoded.timestamps_s), n) or
                not np.all(np.isfinite(encoded.drive)) or np.any(encoded.drive < 0) or np.any(encoded.drive > 1)):
            raise ValueError("Encoded drive must be finite float64 (T,321) in [0,1]")
        if (not isinstance(encoded.channels, np.ndarray) or encoded.channels.dtype != np.float64 or
                encoded.channels.shape != (len(encoded.timestamps_s), 2) or
                not np.all(np.isfinite(encoded.channels)) or np.any(encoded.channels < 0) or np.any(encoded.channels > 1)):
            raise ValueError("Encoded channels must be finite float64 (T,2) in [0,1]")
        if (encoded.encoder_version != VERSION or encoded.config_sha256 != digest(encoder.config) or
                encoded.normalization_sha256 != digest(encoder.normalization)):
            raise ValueError("Encoded version/config/normalization differs from frozen encoder")
        assigned = np.array(encoder.mapping["channel_index"])
        expected = np.zeros_like(encoded.drive)
        expected[:, assigned >= 0] = encoded.channels[:, assigned[assigned >= 0]]
        if not np.array_equal(encoded.drive, expected):
            raise ValueError("Encoded population broadcast or zero DN input violated")
        self.timestamps_s = encoded.timestamps_s.copy()
        self.drive = encoded.drive.copy()
        self.timestamps_s.flags.writeable = False
        self.drive.flags.writeable = False
        self.n = n

    def frame_indices(self, times_ms):
        query = np.asarray(times_ms, dtype=np.float64)
        if query.ndim != 1 or not np.all(np.isfinite(query)):
            raise ValueError("Simulator queries must be finite 1D milliseconds")
        return np.searchsorted(self.timestamps_s, query / 1000.0, side="right") - 1

    def sample(self, times_ms):
        indices = self.frame_indices(times_ms)
        result = np.zeros((len(indices), self.n), dtype=np.float64)
        available = indices >= 0
        result[available] = self.drive[indices[available]]
        return result

    def __call__(self, time_ms, n_neurons):
        if n_neurons != self.n or np.ndim(time_ms) != 0:
            raise ValueError("Simulator callback dimension/time mismatch")
        index = int(self.frame_indices([time_ms])[0])
        return np.zeros(self.n, dtype=np.float64) if index < 0 else self.drive[index].copy()


@dataclass
class ActivityRun:
    encoded: Encoded
    times_ms: np.ndarray
    states: np.ndarray
    step_times_ms: np.ndarray
    step_frame_indices: np.ndarray
    step_drive_unscaled: np.ndarray
    step_input_scaled: np.ndarray
    simulation_config: dict
    metrics: dict
    provenance: dict


class FrozenPipeline:
    def __init__(self):
        self.pipeline_config = load_pipeline_config()
        self.freeze_evidence = verify_frozen()
        self.normalization = json.loads((PHASE / "results/normalization.json").read_text())
        self.encoder = CausalEncoder(load_config(), self.normalization)
        self.circuit = loader.load_circuit()
        if not np.array_equal(self.circuit.body_ids, self.encoder.mapping["body_ids"]):
            raise ValueError("Encoder/simulator node ordering mismatch")
        self.simulation_config = simulator.load_config()
        self.weights = loader.build_signed_weight_matrix(self.circuit, self.simulation_config["sign_map"])

    def run_encoded(self, encoded, duration_ms):
        if isinstance(duration_ms, bool) or not isinstance(duration_ms, (int, float)) or not np.isfinite(duration_ms) or duration_ms <= 0:
            raise ValueError("Explicit finite positive episode duration_ms is required")
        config = deepcopy(self.simulation_config)
        config["duration"] = float(duration_ms)
        simulator.validate_config(config)
        adapter = MillisecondInput(encoded, self.circuit, self.encoder)
        if adapter.timestamps_s[-1] >= duration_ms / 1000.0:
            raise ValueError("Frame timestamps must lie within [0,episode_duration_s)")
        start = time.perf_counter()
        # Phase 4 applies input_scale once, performs Euler updates, and extracts activity.
        times, states, _readout = simulator.run_simulation(self.circuit, config, adapter)
        elapsed = time.perf_counter() - start
        if not np.all(np.isfinite(states)) or np.any(states < 0):
            raise RuntimeError("Simulator returned invalid activity")
        step_times = times[:-1]
        raw = adapter.sample(step_times)
        scaled = raw * config["input_scale"]
        bias = simulator.build_bias_vector(self.circuit, config)
        activation = config["gain"] * (states[:-1] @ self.weights.T) + bias + scaled
        cap = config["clip_max"]
        clipped = 0.0 if cap is None else float(np.mean(activation > cap))
        metrics = dict(runtime_s=elapsed, finite=True, activity_min=float(states.min()),
                       activity_max=float(states.max()), peak_preclip_activation=float(activation.max()),
                       activation_clipped_fraction=clipped, encoder_channel_cap_fraction=float(np.mean(encoded.channels >= 1)),
                       direct_dn_input_max=float(raw[:, np.array(self.encoder.mapping["channel_index"]) < 0].max()),
                       input_unscaled_max=float(raw.max()), input_scaled_max=float(scaled.max()),
                       trainable_parameters=0, numerical_steps=len(step_times), state_samples=len(times))
        provenance = dict(pipeline_version=PIPELINE_VERSION, schema_version="1.0",
                          pipeline_config_sha256=digest(self.pipeline_config), encoder_version=encoded.encoder_version,
                          encoder_config_sha256=encoded.config_sha256, normalization_sha256=encoded.normalization_sha256,
                          simulation_config_sha256=digest(config), circuit_hashes=self.circuit.file_hashes,
                          phase6_freeze_lock_sha256=self.freeze_evidence["phase6_freeze_lock_sha256"],
                          benchmark_manifest_sha256=self.freeze_evidence["manifest_sha256"],
                          units=dict(frame_time="s", state_time="ms", drive="dimensionless arbitrary drive", activity="arbitrary model activity"),
                          initial_state="zeros", warmup_ms=0.0, resampling="causal zero-order hold",
                          state_semantics="x[k] at t[k]; input at t[k] updates x[k+1]; endpoint state is diagnostic only")
        return ActivityRun(encoded, times, states, step_times, adapter.frame_indices(step_times), raw, scaled, config, metrics, provenance)

    def run_frames(self, frames, timestamps_s, duration_ms):
        from connectome.scripts.phase6.dataset import movie_hash
        from connectome.scripts.phase5.stimulus_io import array_hash
        run = self.run_encoded(self.encoder.encode(frames, timestamps_s), duration_ms)
        run.provenance["frame_input"] = dict(shape=list(frames.shape), movie_sha256=movie_hash(frames),
                                            timestamps_sha256=array_hash(timestamps_s))
        return run

    def run_saved(self, directory, stimulus_id):
        frames, timestamps_s, metadata, _config = load_stimulus(directory, stimulus_id)
        if metadata.get("schema_version") != "1.0":
            raise ValueError("Phase 7 requires Phase 5 schema 1.0; legacy files are unsupported")
        # Only the explicit episode end crosses from evaluator metadata to scheduling.
        run = self.run_frames(frames, timestamps_s, metadata["duration_s"] * 1000.0)
        run.provenance["stimulus_source"] = dict(stimulus_id=stimulus_id, schema_version="1.0",
                                                 config_sha256=metadata["config_hash"],
                                                 npz_sha256=file_hash(Path(directory) / f"{stimulus_id}.npz"))
        return run

    def load_frozen_encoded(self, scenario_id):
        index = json.loads((PHASE / "results/encoded_index.json").read_text())
        matches = [row for row in index if row["scenario_id"] == scenario_id]
        if len(matches) != 1:
            raise ValueError("Unknown frozen scenario")
        row = matches[0]
        path = PHASE / row["path"]
        if file_hash(path) != row["sha256"]:
            raise ValueError("Frozen encoded file hash mismatch")
        with np.load(path, allow_pickle=False) as saved:
            if saved["schema_version"].item() != "1.0":
                raise ValueError("Unsupported encoded schema")
            return Encoded(saved["channels"].copy(), saved["drive"].copy(), saved["body_ids"].copy(),
                           saved["timestamps_s"].copy(), {}, saved["encoder_version"].item(),
                           saved["config_sha256"].item(), saved["normalization_sha256"].item())


def save_run(directory, stimulus_id, run, *, overwrite=False):
    """Keep all generated files in Phase 7; never overwrite an earlier phase."""
    from connectome.scripts.phase5.config import validate_id
    validate_id(stimulus_id)
    directory = Path(directory).resolve()
    if not directory.is_relative_to(ROOT / "connectome/phase7"):
        raise ValueError("Activity output must stay within connectome/phase7")
    directory.mkdir(parents=True, exist_ok=True)
    paths = [directory / f"{stimulus_id}{suffix}" for suffix in (".npz", "_config.json", "_metadata.json")]
    if not overwrite and any(p.exists() for p in paths):
        raise FileExistsError("Activity run already exists; specify overwrite explicitly")
    np.savez_compressed(paths[0], schema_version=np.array("1.0"), times_ms=run.times_ms,
                        states=run.states, body_ids=run.encoded.body_ids, frame_timestamps_s=run.encoded.timestamps_s,
                        channels=run.encoded.channels, frame_drive=run.encoded.drive,
                        step_times_ms=run.step_times_ms, step_frame_indices=run.step_frame_indices,
                        step_drive_unscaled=run.step_drive_unscaled, step_input_scaled=run.step_input_scaled)
    write_json(paths[1], run.simulation_config)
    write_json(paths[2], dict(provenance=run.provenance, metrics=run.metrics,
                             arrays_sha256=file_hash(paths[0]), config_file_sha256=file_hash(paths[1]),
                             invocation=[sys.executable, *sys.argv],
                             environment=dict(python=platform.python_version(), numpy=np.__version__,
                                              pyyaml=yaml.__version__, platform=platform.platform())))
    return paths
