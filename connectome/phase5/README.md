# Phase 5: synthetic visual stimuli

This module generates static, translating and looming circles as grayscale uint8 frames. All visual positions and radii are pixels. It provides a documented frame interface for downstream consumers; no neural processing is implemented.

## Usage

Run from the repository root with the existing virtual environment (NumPy, PyYAML, Matplotlib and pytest). No new dependencies were added.

```bash
./venv/bin/python -m connectome.scripts.phase5.run_stimulus --config connectome/phase5/stimulus_config.yaml
./venv/bin/python -m connectome.scripts.phase5.run_stimulus --config connectome/phase5/examples/static.yaml
./venv/bin/python -m connectome.scripts.phase5.run_stimulus --config connectome/phase5/examples/translating.yaml
```

Default output is `connectome/phase5/results/samples/`. `--out-dir PATH` selects another directory. Existing stimulus IDs require `--overwrite`; an invalid run is rejected before writing files.

Each run saves `<id>.npz` (lossless frames/timestamps), `<id>_metadata.json` (parameters, per-frame time/geometry and hashes) and `<id>_config.yaml` (validated snapshot including dimension defaults). Regeneration may change the UTC run date; frame arrays, timestamps and content/config hashes are deterministic.

```bash
./venv/bin/python -m pytest connectome/phase5/tests/ -q
MPLCONFIGDIR=/tmp/fly-phase5-mpl ./venv/bin/python -m connectome.scripts.phase5.validate_phase5
./venv/bin/python -m connectome.scripts.phase5.generate_report
```

The validation command runs the full suite, generates seven saved examples and seven plots, verifies saved arrays through the loader, and checks Phase 3/4 content hashes. Detailed evidence is under `results/`, including test logs/XML, sample measurements and protected-file hashes. Diagnostics alone: `./venv/bin/python -m connectome.scripts.phase5.diagnostics` (the older script-path invocation also works). Plotting uses Agg and does not need a display.

## Configuration reference

YAML must be a mapping; unknown fields fail to catch misspellings. All numeric fields must be finite builtin numbers, excluding booleans; absolute value is limited to 1e12. More specific bounds below take precedence.

| Field | Units / constraints |
| --- | --- |
| `stimulus_id` | Required; 1–80 chars, first alphanumeric, then alphanumeric/underscore/hyphen. Used as a filename prefix. |
| `stimulus_type` | Required: `static`, `translating`, `looming`, `control_static`, `control_translating`, `control_background`. |
| `width`, `height` | Pixels; default 256 each; integer 1–8192. Non-square frames supported. |
| `fps` | Frames/s; required, positive; fractional values allowed. |
| `duration_ms` | Requested run duration in ms; required, positive. At least one frame. |
| `background_intensity`, `object_intensity` | Required integers 0–255. Dark objects and zero contrast are allowed. |
| `initial_position` | Required `[x,y]` in pixels; fractional and offscreen centers allowed, rendered with clipping. |
| `initial_radius` | Required radius in px, >=0. Zero means no object. Looming uses `f_R/Z(t)` instead of this field. |
| `shape` | Required `circle`. |
| `start_time_ms` | Required >=0 ms; translation starts moving then. The object is visible from frame 0. Static stimuli ignore it; looming uses its own onset. |
| `random_seed` | Required integer 0–2^32-1; provenance only because rendering uses no randomness. |
| `speed_px_per_s` | Required for translation; >=0 px/s. Zero is stationary. |
| `motion_direction_deg` | Required for translation; image-plane direction, 0 right, 90 up, 180 left, 270 down. Any finite direction is reduced modulo 360. These are not biological visual angles. |
| `expansion_params` | Required for looming; fields described below. Retained parameters on controls are validated but do not drive their motion. |
| `rendering_translation_tolerance`, `rendering_radius_tolerance` | Legacy optional >=0 px fields retained as provenance. They do not alter rendering; diagnostic acceptance uses an explicit 1 px bound. |

Frame count is `floor(duration_ms / 1000 * fps)` using float arithmetic; runs producing 0 or more than 1,000,000 frames fail. Allocation is limited to 256 MiB for the uint8 frame array; total process memory is higher due to masks, hashes and serialization. Translation endpoints must remain within the 1e12 coordinate limit. Fully offscreen objects yield background; very large valid radii can fill every pixel.

## Looming model and assumptions

The sole looming model is a **physically motivated pinhole projection in abstract units**, not a calibrated eye model:

`Z(t) = Z0 - v * max(0, t - t_onset_ms/1000)` and `r(t) = f_R / Z(t)`.

This assumes constant approach speed along the viewing axis, fixed object size, fixed circle center and a planar image. `Z0` and optional `min_distance` are abstract distances; `v` is abstract distance/s; `f_R` is px × abstract distance. Require `f_R > 0`, `v >= 0`, `t_onset_ms >= 0`, and `Z0 > min_distance > 0`. The default `min_distance=1.0` preserves the earlier simulator margin; it is a modeling choice, not biological evidence. `Z` must exceed that margin throughout the entire requested interval, including the duration endpoint. Collision/post-collision runs fail rather than clipping the denominator. Onset after duration and `v=0` are stationary controls.

`initial_radius` remains in looming configs for API compatibility but the effective initial radius is `f_R/Z0`. The supplied config makes them consistent. `control_static` behaves exactly as `static`; `control_translating` behaves exactly as `translating`. Matching is the caller's responsibility: use the same initial radius, position and contrast. `control_background` hides the circle throughout.

## Downstream interface (schema 1.0)

```python
from connectome.scripts.phase5.loader import load_stimulus
frames, timestamps_s, metadata, config = load_stimulus(
    "connectome/phase5/results/samples", "diag_looming")
# frames: (T, H, W), uint8, values 0..255
# timestamps_s: (T,), float64, t[i] = i/fps, starting at 0
```

The existing four-value return and call signature are retained. See `specification.md` for the exact temporal/metadata contract. The loader verifies schema, config, dimensions, timestamps, geometry, array hashes and YAML snapshot. Unknown schema versions fail. Legacy unversioned files are accepted with basic config/array checks and a warning; they do not provide frame integrity verification. Regenerate them for schema 1.0.

## Limitations

One circular object per run, instantaneous sampling, no anti-aliasing, blur, optics, calibrated visual angles or retinotopy. Raster area radius and centroid are quantized and can become misleading under clipping or zero contrast; analytic geometry is saved separately. No biologically validated processing or encoding is claimed. See the audit and validation report for session evidence and remaining limitations.
