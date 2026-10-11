"""Validated Phase 5 config, with explicit memory and numerical limits."""
from copy import deepcopy
from pathlib import Path
import math
import json
import re
import yaml

MAX_FRAME_BYTES = 256 * 1024 * 1024
MAX_FRAMES = 1_000_000
NUMERIC_LIMIT = 1e12
TYPES = {"static", "translating", "looming", "control_static",
         "control_translating", "control_background"}
REQUIRED = {"stimulus_id", "stimulus_type", "fps", "duration_ms",
            "background_intensity", "object_intensity", "initial_position",
            "initial_radius", "shape", "start_time_ms", "random_seed"}
OPTIONAL = {"width", "height", "expansion_params", "motion_direction_deg",
            "speed_px_per_s", "rendering_translation_tolerance", "rendering_radius_tolerance"}


def number(value, name, minimum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    if abs(value) > NUMERIC_LIMIT or not math.isfinite(value):
        raise ValueError(f"{name} must be finite with absolute value <= {NUMERIC_LIMIT:g}")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def validate_id(stimulus_id):
    if not isinstance(stimulus_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", stimulus_id):
        raise ValueError("stimulus_id must be a safe 1–80 character filename identifier")


def frame_count(duration_ms, fps):
    number(duration_ms, "Duration", 0)
    number(fps, "FPS", 0)
    if duration_ms == 0 or fps == 0:
        raise ValueError("Duration and FPS must be positive")
    count = math.floor(duration_ms / 1000.0 * fps)
    if not 1 <= count <= MAX_FRAMES:
        raise ValueError(f"Frame count must be between 1 and {MAX_FRAMES}")
    return count


def validate_config(config):
    """Return an independent validated snapshot. Dimensions default to 256."""
    if not isinstance(config, dict):
        raise ValueError("Configuration must be a mapping")
    if not all(isinstance(key, str) for key in config):
        raise ValueError("Configuration keys must be strings")
    missing = REQUIRED - config.keys()
    if missing:
        raise ValueError(f"Missing required config field: {sorted(missing)[0]}")
    unknown = config.keys() - REQUIRED - OPTIONAL
    if unknown:
        raise ValueError(f"Unknown config fields: {sorted(unknown)}")
    c = deepcopy(config)
    c.setdefault("width", 256)
    c.setdefault("height", 256)
    validate_id(c["stimulus_id"])
    if not isinstance(c["stimulus_type"], str) or c["stimulus_type"] not in TYPES:
        raise ValueError(f"Invalid stimulus_type: {c['stimulus_type']}")
    if c["shape"] != "circle":
        raise ValueError("Only 'circle' shape is supported.")
    for key in ("width", "height"):
        if type(c[key]) is not int or not 1 <= c[key] <= 8192:
            raise ValueError("Dimensions must be positive integers <= 8192")
    if number(c["duration_ms"], "Duration") <= 0:
        raise ValueError("Duration must be positive")
    n = frame_count(c["duration_ms"], c["fps"])
    if n * c["width"] * c["height"] > MAX_FRAME_BYTES:
        raise ValueError("Frame array exceeds the 256 MiB memory budget")
    for key in ("background_intensity", "object_intensity"):
        if type(c[key]) is not int or not 0 <= c[key] <= 255:
            raise ValueError(f"{key} must be an integer in [0, 255]")
    pos = c["initial_position"]
    if not isinstance(pos, (list, tuple)) or len(pos) != 2:
        raise ValueError("initial_position must contain [x, y]")
    c["initial_position"] = [number(x, "position") for x in pos]
    number(c["initial_radius"], "initial_radius", 0)
    number(c["start_time_ms"], "start_time_ms", 0)
    if type(c["random_seed"]) is not int or not 0 <= c["random_seed"] <= 2**32 - 1:
        raise ValueError("random_seed must be an integer in [0, 2**32-1]")
    for key in ("rendering_translation_tolerance", "rendering_radius_tolerance"):
        if key in c:
            number(c[key], key, 0)
    if "speed_px_per_s" in c:
        number(c["speed_px_per_s"], "speed_px_per_s", 0)
    if "motion_direction_deg" in c:
        number(c["motion_direction_deg"], "motion_direction_deg")
    if c["stimulus_type"] in {"translating", "control_translating"}:
        for key in ("motion_direction_deg", "speed_px_per_s"):
            if key not in c:
                raise ValueError(f"Translating stimulus requires {key}")
        number(c["motion_direction_deg"], "motion_direction_deg")
        number(c["speed_px_per_s"], "speed_px_per_s", 0)
        displacement = c["speed_px_per_s"] * max(0, (c["duration_ms"] - c["start_time_ms"]) / 1000)
        if displacement + max(abs(x) for x in pos) > NUMERIC_LIMIT:
            raise ValueError("Translation trajectory exceeds numerical coordinate limits")
    if c["stimulus_type"] == "looming" or "expansion_params" in c:
        ep = c.get("expansion_params")
        if not isinstance(ep, dict) or not {"f_R", "Z0", "v", "t_onset_ms"} <= ep.keys():
            raise ValueError("Looming stimulus requires expansion_params: f_R, Z0, v, t_onset_ms")
        if ep.keys() - {"f_R", "Z0", "v", "t_onset_ms", "min_distance"}:
            raise ValueError("Unknown expansion_params fields")
        for key in ep:
            number(ep[key], key, 0)
        margin = ep.get("min_distance", 1.0)
        if margin <= 0 or ep["f_R"] <= 0 or ep["Z0"] <= margin:
            raise ValueError("Require f_R > 0 and Z0 > min_distance > 0")
        z_end = ep["Z0"] - ep["v"] * max(0, (c["duration_ms"] - ep["t_onset_ms"]) / 1000)
        if c["stimulus_type"] == "looming" and z_end <= margin:
            raise ValueError("Looming collision/negative distance: Z must exceed min_distance throughout duration")
        if c["stimulus_type"] == "looming" and ep["f_R"] / z_end > NUMERIC_LIMIT:
            raise ValueError("Looming radius exceeds numerical limits")
    try:
        json.dumps(c, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("Configuration must contain finite JSON-compatible values") from exc
    return c


def load_config(path: str | Path) -> dict:
    with Path(path).open() as f:
        return validate_config(yaml.safe_load(f))
