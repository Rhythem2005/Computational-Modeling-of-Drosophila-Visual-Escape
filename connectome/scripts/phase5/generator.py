"""Deterministic circular stimuli in pixel coordinates; no neural encoding."""
import numpy as np
from .config import validate_config, frame_count


def compute_timestamps(duration_ms: float, fps: float) -> np.ndarray:
    return np.arange(frame_count(duration_ms, fps), dtype=np.float64) / fps


def _trajectory(c, timestamps):
    centers = np.tile(np.asarray(c["initial_position"], dtype=np.float64), (len(timestamps), 1))
    radii = np.full(len(timestamps), c["initial_radius"], dtype=np.float64)
    stype = c["stimulus_type"]
    if stype == "control_background":
        radii.fill(0)
    if stype in {"translating", "control_translating"}:
        dt = np.maximum(0, timestamps - c["start_time_ms"] / 1000)
        theta = np.deg2rad(c["motion_direction_deg"] % 360)
        centers[:, 0] += np.cos(theta) * c["speed_px_per_s"] * dt
        centers[:, 1] -= np.sin(theta) * c["speed_px_per_s"] * dt
    if stype == "looming":
        ep = c["expansion_params"]
        z = ep["Z0"] - ep["v"] * np.maximum(0, timestamps - ep["t_onset_ms"] / 1000)
        radii = ep["f_R"] / z
    return centers, radii


def compute_trajectory(config):
    """Return analytic centers [T,2] and radii [T], both in pixels."""
    c = validate_config(config)
    return _trajectory(c, compute_timestamps(c["duration_ms"], c["fps"]))


def _render(width, height, bg, obj, cx, cy, radius, grid=None):
    frame = np.full((height, width), bg, dtype=np.uint8)
    if radius == 0:
        return frame
    y, x = np.ogrid[:height, :width] if grid is None else grid
    frame[(x - cx)**2 + (y - cy)**2 <= radius**2] = obj
    return frame


def render_frame(width, height, bg_intensity, obj_intensity, cx, cy, r):
    c = validate_config(dict(stimulus_id="frame", stimulus_type="static", width=width,
        height=height, background_intensity=bg_intensity, object_intensity=obj_intensity,
        initial_position=[cx, cy], initial_radius=r, shape="circle", fps=1,
        duration_ms=1000, start_time_ms=0, random_seed=0))
    return _render(c["width"], c["height"], bg_intensity, obj_intensity, cx, cy, r)


def generate_stimulus(config: dict) -> tuple[np.ndarray, np.ndarray]:
    c = validate_config(config)
    timestamps = compute_timestamps(c["duration_ms"], c["fps"])
    centers, radii = _trajectory(c, timestamps)
    frames = np.empty((len(timestamps), c["height"], c["width"]), dtype=np.uint8)
    grid = np.ogrid[:c["height"], :c["width"]]
    for i, ((cx, cy), r) in enumerate(zip(centers, radii)):
        frames[i] = _render(c["width"], c["height"], c["background_intensity"],
                            c["object_intensity"], cx, cy, r, grid)
    return frames, timestamps
