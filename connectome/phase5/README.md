# Phase 5: Synthetic Visual-Stimulus Generator

## Purpose
Phase 5 provides a fully deterministic, synthetic visual-stimulus generator to supply frames for the computational network model of `circuit_v2`. It creates standardized motion paradigms (looming, translating, static controls) used to probe visual escape responses.

## Scope
- Generates geometric synthetic stimuli (expanding circles, translating circles).
- Deterministic rendering (hard-edged Euclidean distance threshold).
- Lossless serialization (saving directly to compressed `.npz`).
- Out of scope: calibrated fly visual fields, photoreceptor spatial sampling, optical flow computation, behavioral tracking.

## Stimulus Types
- `static`: A stationary circle at a fixed position.
- `translating`: A circle moving at a constant speed in a given direction without expanding.
- `looming`: A circle expanding according to the synthetic geometric model $r(t) = f \cdot R / Z(t)$, simulating approach.
- Matched controls (`control_static`, `control_translating`, `control_background`): Identical background/object intensities and properties, explicitly lacking a specific feature (e.g. no expansion, or no object at all).

## Configuration
Configuration is defined via YAML (e.g., `stimulus_config.yaml`). Required fields:
- `stimulus_id`, `stimulus_type`
- `width`, `height`, `fps`, `duration_ms`
- `background_intensity`, `object_intensity`
- `initial_position`, `initial_radius`, `shape` (only `circle` supported)
- `random_seed`, `start_time_ms`

Looming models require `expansion_params` (`f_R`, `Z0`, `v`, `t_onset_ms`).
Translating models require `motion_direction_deg` and `speed_px_per_s`.

## How to Generate & Test
To run validation tests:
```bash
./venv/bin/python -m pytest connectome/scripts/phase5/tests/
```

To run diagnostics:
```bash
./venv/bin/python connectome/scripts/phase5/diagnostics.py
```
Generated diagnostic images are saved to `connectome/phase5/reports/`.

## Phase 6 API Consumption
Phase 6 (not yet implemented) will consume these stimuli via `connectome.scripts.phase5.loader.load_stimulus()`.
Example:
```python
from connectome.scripts.phase5.loader import load_stimulus
# Returns frames (T, H, W) uint8, timestamps (T) float, metadata dict, config dict
frames, timestamps, meta, config = load_stimulus("connectome/phase5/results/", "test_looming_1")
```

## Limitations
- This is a synthetic rendering pipeline; it explicitly does NOT represent a calibrated biological fly eye visual field.
- Units are strictly generic pixels and seconds.
