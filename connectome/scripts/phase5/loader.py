"""Stable frame-array interface for downstream consumers."""
import json
import warnings
from datetime import datetime
from pathlib import Path
import numpy as np
import yaml
from .config import validate_config, validate_id
from .stimulus_io import SCHEMA_VERSION, generate_metadata, validate_arrays, config_hash


def load_stimulus(data_dir, stimulus_id):
    """Return (frames [T,H,W] uint8, timestamps [T] float64, metadata, config)."""
    validate_id(stimulus_id)
    folder = Path(data_dir)
    with (folder / f"{stimulus_id}_metadata.json").open() as f:
        meta = json.load(f)
    if not isinstance(meta, dict) or "config_snapshot" not in meta:
        raise ValueError("Missing metadata config_snapshot")
    version = meta.get("schema_version")
    if version not in (None, SCHEMA_VERSION):
        raise ValueError(f"Unsupported stimulus schema_version: {version}")
    c = validate_config(meta["config_snapshot"])
    if c["stimulus_id"] != stimulus_id or meta.get("stimulus_id") != stimulus_id:
        raise ValueError("stimulus_id does not match stored config")
    with np.load(folder / f"{stimulus_id}.npz", allow_pickle=False) as data:
        if set(data.files) != {"frames", "timestamps_s"}:
            raise ValueError("Unexpected NPZ arrays")
        frames, timestamps = data["frames"], data["timestamps_s"]
    validate_arrays(c, frames, timestamps)
    if version is None:
        if meta.get("config_hash") != config_hash(meta["config_snapshot"]):
            raise ValueError("Legacy config hash mismatch")
        warnings.warn("Legacy unversioned metadata: frame integrity is unavailable; regenerate for schema 1.0", UserWarning)
    else:
        versions = meta.get("library_versions")
        if not isinstance(versions, dict) or not all(isinstance(versions.get(k), str) and versions[k] for k in ("numpy", "pyyaml", "python")):
            raise ValueError("Missing or invalid library_versions")
        try:
            date = datetime.fromisoformat(meta["run_date"])
            if date.utcoffset() is None or date.utcoffset().total_seconds() != 0:
                raise ValueError("run_date must be a timezone-aware UTC timestamp")
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Invalid run_date") from exc
        expected = generate_metadata(c, frames, timestamps)
        for key, value in expected.items():
            if key not in {"run_date", "library_versions"} and meta.get(key) != value:
                raise ValueError(f"Metadata mismatch: {key}")
        snapshot = folder / f"{stimulus_id}_config.yaml"
        if not snapshot.exists() or yaml.safe_load(snapshot.read_text()) != c:
            raise ValueError("Missing or inconsistent config snapshot file")
    return frames, timestamps, meta, c
