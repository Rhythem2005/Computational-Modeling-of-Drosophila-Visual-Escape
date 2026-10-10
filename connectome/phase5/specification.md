# Phase 5 Specification

## 1. Frame Representation and Coordinates
**IMPLEMENTATION FACT:**
- Frames are represented as 2D `uint8` numpy arrays.
- Coordinates follow standard image conventions: Origin `(0,0)` is at the top-left corner, $+x$ points right, $+y$ points down.
- Rasterization uses a strictly deterministic, hard-edged Euclidean distance threshold without sub-pixel anti-aliasing. A pixel at `(x, y)` is set to the object intensity if `(x - cx)^2 + (y - cy)^2 <= r^2`, otherwise it assumes background intensity.

## 2. Timing
**IMPLEMENTATION FACT:**
- Frame count is defined exactly as `floor(duration_s * fps)`.
- Timestamps represent the ideal simulation time of the frame, given by `i / fps` (where `i` is the frame index starting from 0).

## 3. Equations and Looming Model
**STIMULUS-MODEL ASSUMPTION:**
Looming stimuli use a synthetic geometric model that mimics an object approaching at constant velocity $v$:
$$ Z(t) = Z_0 - v \cdot (t - t_{\text{onset}}) $$
$$ r(t) = \frac{f \cdot R}{Z(t)} $$
where $Z_0$ is the initial distance, $f \cdot R$ is a size parameter, and expansion only begins for $t > t_{\text{onset}}$. Before onset, the object remains at a constant radius $r = (f \cdot R)/Z_0$.

**IMPLEMENTATION FACT:**
If the expansion trajectory leads to $Z(t) \le 1.0$ at the final frame, the configuration explicitly raises an error during validation to prevent a zero-distance division singularity (collision) or negative distance.

## 4. Reproducibility Guarantees
**IMPLEMENTATION FACT:**
- The rendering is perfectly deterministic for a given configuration and seed.
- Two identical configuration parameters will produce bitwise-identical output arrays.
- Metadata saved with the arrays explicitly contains the snapshot of the configuration, the SHA-256 hash of the configuration, and library dependencies used during generation.

## 5. Interface Contract (Phase 6 API)
**IMPLEMENTATION FACT:**
The output loader strictly exposes:
- `frames`: `ndarray [T, H, W]` (`uint8`)
- `timestamps_s`: `ndarray [T]` (`float`)
- `metadata`: `dict`
- `config`: `dict`
No neural precomputations, labels, or feature extractions are performed in this phase.
