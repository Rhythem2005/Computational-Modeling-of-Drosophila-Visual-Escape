"""Read immutable Phase 7 activity; save Phase 8 requests separately."""
import json
from pathlib import Path
import platform
import sys

import numpy as np

from connectome.scripts.phase5.config import validate_id
from connectome.scripts.phase6.encoder import digest
from connectome.scripts.phase4 import simulator
from connectome.scripts.phase7.pipeline import FrozenPipeline
from .evidence import ROOT, PHASE, file_hash, write_json
from .decoder import InitiationDecoder, VERSION, load_config


def load_activity(directory, stimulus_id):
    validate_id(stimulus_id)
    directory = Path(directory)
    npz = directory / f"{stimulus_id}.npz"
    config_path = directory / f"{stimulus_id}_config.json"
    meta_path = directory / f"{stimulus_id}_metadata.json"
    metadata = json.loads(meta_path.read_text())
    config = json.loads(config_path.read_text())
    if metadata["arrays_sha256"] != file_hash(npz) or metadata["config_file_sha256"] != file_hash(config_path):
        raise ValueError("Saved Phase 7 activity/config hash mismatch")
    expected = simulator.load_config()
    expected["duration"] = config.get("duration")
    if config != expected:
        raise ValueError("Activity config differs from the frozen Phase 4 condition")
    simulator.validate_config(config)
    pipeline = FrozenPipeline()
    provenance = metadata["provenance"]
    required = dict(encoder_version="1.0.0", pipeline_version="1.0.0",
                    normalization_sha256=digest(pipeline.normalization),
                    encoder_config_sha256=digest(pipeline.encoder.config),
                    phase6_freeze_lock_sha256=pipeline.freeze_evidence["phase6_freeze_lock_sha256"],
                    simulation_config_sha256=digest(config), circuit_hashes=pipeline.circuit.file_hashes)
    if any(provenance.get(k) != value for k, value in required.items()):
        raise ValueError("Activity provenance differs from the frozen pipeline")
    with np.load(npz, allow_pickle=False) as saved:
        if saved["schema_version"].item() != "1.0":
            raise ValueError("Unsupported activity schema")
        times = saved["times_ms"].copy()
        states = saved["states"].copy()
        body_ids = saved["body_ids"].copy()
    if times.shape != (round(config["duration"]) + 1,) or times[-1] != config["duration"]:
        raise ValueError("Saved activity must contain initial and diagnostic endpoint samples")
    return times, states, body_ids, config["duration"], dict(
        activity_npz_sha256=file_hash(npz), activity_config_sha256=file_hash(config_path),
        source_provenance=provenance)


def save_decoded(directory, stimulus_id, decoded, source, *, overwrite=False):
    validate_id(stimulus_id)
    directory = Path(directory).resolve()
    if not directory.is_relative_to(PHASE.resolve()):
        raise ValueError("Decoded output must stay within Phase 8")
    paths = [directory / f"{stimulus_id}{suffix}" for suffix in (".npz", "_action.json", "_metadata.json")]
    if not overwrite and any(p.exists() for p in paths):
        raise FileExistsError("Decoded episode exists; overwrite must be explicit")
    directory.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(paths[0], schema_version=np.array("1.0"), decoder_version=np.array(VERSION),
        times_ms=decoded.times_ms, score=decoded.score, sustained_score=decoded.sustained_score,
        eligible=decoded.eligible, escape_event=decoded.escape_event, escape_requested=decoded.escape_requested,
        dn_body_ids=decoded.dn_body_ids, dn_activity=decoded.dn_activity)
    write_json(paths[1], decoded.action())
    write_json(paths[2], dict(decoder_config_sha256=digest(load_config()), source=source,
        decoded_npz_sha256=file_hash(paths[0]), action_file_sha256=file_hash(paths[1]),
        threshold=decoded.threshold.as_dict(), threshold_status=decoded.threshold_status,
        decoder_version=VERSION, threshold_amendment_id=None if decoded.threshold_status == "original_rule_audit" else "fly_decoder_thresholds_v1_1",
        units=dict(time="ms", score="arbitrary model activity", steering="unavailable"),
        invocation=[sys.executable, *sys.argv], environment=dict(python=platform.python_version(), numpy=np.__version__)))
    return paths
