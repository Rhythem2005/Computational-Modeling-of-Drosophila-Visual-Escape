"""Versioned frames, temporal metadata and reproducible config snapshots."""
import hashlib
import json
import os
import platform
import tempfile
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import yaml
from .config import validate_config
from .generator import compute_timestamps, compute_trajectory

SCHEMA_VERSION = "1.0"


def config_hash(config):
    return hashlib.sha256(json.dumps(config, sort_keys=True, allow_nan=False).encode()).hexdigest()


def array_hash(array):
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def validate_arrays(config, frames, timestamps):
    expected = compute_timestamps(config["duration_ms"], config["fps"])
    if not isinstance(frames, np.ndarray) or frames.dtype != np.uint8 or frames.shape != (len(expected), config["height"], config["width"]):
        raise ValueError("frames must be uint8 with layout (T, H, W) matching config")
    if not isinstance(timestamps, np.ndarray) or timestamps.dtype != np.float64 or not np.array_equal(timestamps, expected):
        raise ValueError("timestamps_s must be float64 i/fps matching config")
    if not np.all((frames == config["background_intensity"]) | (frames == config["object_intensity"])):
        raise ValueError("Frame intensities do not match config")


def generate_metadata(config, frames, timestamps):
    c = validate_config(config)
    validate_arrays(c, frames, timestamps)
    centers, radii = compute_trajectory(c)
    meta = dict(
        schema_version=SCHEMA_VERSION, stimulus_id=c["stimulus_id"],
        stimulus_type=c["stimulus_type"], frame_layout="THW", frame_dtype="uint8",
        dimensions={"width": c["width"], "height": c["height"]}, fps=c["fps"],
        n_frames=len(timestamps), duration_s=c["duration_ms"] / 1000,
        timestamps_s=timestamps.tolist(), timestamp_origin="run start at 0 s",
        timestamp_semantics="instantaneous frame at i/fps; requested interval [0,duration_s)",
        geometry=c["shape"], center_xy_px=centers.tolist(), radius_px=radii.tolist(),
        intensities={"background": c["background_intensity"], "object": c["object_intensity"]},
        random_seed=c["random_seed"], randomness="none; random_seed is provenance only",
        coordinate_convention="origin top-left, +x right, +y down; integer pixel centers",
        direction_convention="0 degrees right, 90 degrees up, counterclockwise",
        rendering_method="hard-edged Euclidean distance threshold; radius=0 hides object",
        units={"position": "px", "radius": "px", "time": "s", "speed": "px/s",
               "direction": "image-plane degrees", "Z0": "abstract distance",
               "v": "abstract distance/s", "f_R": "px * abstract distance"},
        model="physically motivated pinhole projection in abstract units" if c["stimulus_type"] == "looming" else "synthetic geometric stimulus",
        config_snapshot=c, config_hash=config_hash(c), frames_sha256=array_hash(frames),
        timestamps_sha256=array_hash(timestamps),
        library_versions={"numpy": np.__version__, "pyyaml": yaml.__version__, "python": platform.python_version()},
        run_date=datetime.now(timezone.utc).isoformat())
    if c["stimulus_type"] in {"translating", "control_translating"}:
        meta["motion_params"] = {"direction_deg": c["motion_direction_deg"], "speed_px_per_s": c["speed_px_per_s"]}
    if c["stimulus_type"] == "looming":
        meta["expansion_params"] = c["expansion_params"]
    return meta


def save_stimulus(out_dir, config, frames, timestamps, *, overwrite=False):
    """Write NPZ, JSON metadata and YAML snapshot. Existing runs require opt-in."""
    c = validate_config(config)
    meta = generate_metadata(c, frames, timestamps)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    sid = c["stimulus_id"]
    paths = [out / f"{sid}.npz", out / f"{sid}_metadata.json", out / f"{sid}_config.yaml"]
    if not overwrite and any(p.exists() for p in paths):
        raise FileExistsError(f"Stimulus {sid} already exists; use overwrite=True")
    temporary = []
    try:
        for path in paths:
            fd, name = tempfile.mkstemp(prefix=f".{sid}-", dir=out)
            os.close(fd)
            temporary.append(Path(name))
        with temporary[0].open("wb") as f:
            np.savez_compressed(f, frames=frames, timestamps_s=timestamps)
        temporary[1].write_text(json.dumps(meta, indent=2, allow_nan=False) + "\n")
        temporary[2].write_text(yaml.safe_dump(c, sort_keys=True))
        for src, dst in zip(temporary, paths):
            src.replace(dst)
    finally:
        for p in temporary:
            p.unlink(missing_ok=True)
    return paths[0], paths[1]
