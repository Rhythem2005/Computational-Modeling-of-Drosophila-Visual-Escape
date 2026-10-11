# Phase 5 frame interface — schema 1.0

## Frames and time

- `frames`: NumPy ndarray, uint8, `(T,H,W)`, grayscale; `T=floor(duration_ms/1000*fps)`, positive.
- `timestamps_s`: NumPy ndarray, float64, `(T,)`, exactly `arange(T)/fps`. Each frame samples one instant. Time is relative to run start, not wall-clock time. `start_time_ms` affects translation motion, never timestamp origin.
- Requested time interval is `[0,duration_s)`. Last sample is `(T-1)/fps`; for noninteger duration×fps, floor deliberately omits the trailing partial frame. No endpoint frame or exposure interval is inferred.
- Image origin `(0,0)` is top-left. Integer `(x,y)` denotes a pixel center, x grows right, y grows down. Fractional centers/radii use a hard distance test `(x-cx)^2+(y-cy)^2 <= radius^2`. Radius zero explicitly hides the object.

## Geometry

Static center/radius are constant. Translation uses `dt=max(0,t-start_time_ms/1000)`, `cx=cx0+speed*cos(direction)*dt`, `cy=cy0-speed*sin(direction)*dt`. Object presence begins at frame 0. Directions are image-plane degrees, not visual-field angles. Looming uses `Z=Z0-v*max(0,t-t_onset_ms/1000)` and `r=f_R/Z`, with center fixed. This is a physically motivated pinhole model in abstract units. Validation checks the full requested duration against `min_distance` (default 1), even when the endpoint is unsampled. Controls are aliases as documented in README; no automatic matching is implied.

## Files

`<id>.npz` contains exactly `frames` and `timestamps_s`; loading uses `allow_pickle=False`. `<id>_metadata.json` is UTF-8 JSON with finite numbers. `<id>_config.yaml` contains the complete validated config. Each file is replaced atomically, but the three-file set is not a filesystem transaction; interruption can yield an incomplete run and the loader rejects inconsistencies. Existing IDs need explicit overwrite.

## Metadata keys

| Fields | Contract |
| --- | --- |
| `schema_version` | String `1.0`; exact-version support, unknown versions rejected. |
| `stimulus_id`, `stimulus_type`, `geometry` | Config identity/type and `circle`. |
| `frame_layout`, `frame_dtype` | `THW`, `uint8`. |
| `dimensions`, `n_frames`, `fps`, `duration_s` | Width/height mapping, integer T, rate in frames/s, requested duration in seconds. |
| `timestamps_s`, `timestamp_origin`, `timestamp_semantics` | List of T seconds, run origin and instantaneous sampling convention. Must equal the NPZ timestamps. |
| `center_xy_px`, `radius_px` | T pairs of analytic center coordinates and T analytic radii, before clipping/rasterization. These are stimulus geometry, not neural features. Background controls have radius zero. |
| `intensities`, `random_seed`, `randomness` | Object/background integer values, config seed, declaration that rendering uses no randomness. |
| `coordinate_convention`, `direction_convention`, `rendering_method`, `units`, `model` | Explicit coordinates, model classification and unit labels. See README. |
| `config_snapshot`, `config_hash` | Independent normalized config and SHA-256 of UTF-8 `json.dumps(config, sort_keys=True, allow_nan=False)`. Width/height defaults are explicit; default min_distance semantics remain 1.0 when absent. |
| `frames_sha256`, `timestamps_sha256` | SHA-256 of contiguous array bytes in C order; native float64 timestamp bytes (current runtime uses little endian). The NPZ stores array dtype/layout. |
| `library_versions`, `run_date` | Producer NumPy/PyYAML/Python versions and timezone-aware UTC ISO timestamp; run date is not deterministic. |
| `motion_params` | Translation types only: `direction_deg`, `speed_px_per_s`. |
| `expansion_params` | Looming only: config expansion mapping. |

`load_stimulus(directory,id)` returns `(frames,timestamps_s,metadata,config)` and validates config, schema fields, trajectories, dimensions, exact timestamps, allowed pixel intensities, content hashes and matching YAML snapshot. Legacy versionless JSON remains readable with a warning and lacks content-hash guarantees. Extra metadata fields may be ignored within 1.0; mandatory fields are checked. Invalid or missing run files fail explicitly.

## Reproducibility and bounds

No random samples are drawn. Identical config in the same runtime produces identical frames, timestamps and config/content hashes regardless of the process random state. Arbitrary frame geometry is clipped at the image boundary; offscreen positions are valid. Finite numeric bounds, allocation and looming validity constraints are specified in README and enforced by `validate_config` on generation, saving, loading and YAML ingestion.
