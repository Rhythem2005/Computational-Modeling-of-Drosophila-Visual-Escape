# Phase 6 — causal visual encoder

Read [the predeclared specification](specification.md) for equations, numerical gates, fitting budget and limitations. This phase implements only frame-to-drive encoding, not neural simulation/integration or escape decisions. Primary representation is two global engineered channels broadcast uniformly to Circuit v2 LC4 and LPLC2 populations. DN input is exactly zero.

From repository root, using existing dependencies:

```bash
./venv/bin/python -m connectome.scripts.phase6.regression
./venv/bin/python -m pytest connectome/phase6/tests/ -q
./venv/bin/python -m connectome.scripts.phase6.validate_phase6
```

The regression command runs the existing Phase 4/5/5.5 tests and redirects the separate 159-assertion Phase 4 integration suite's output to `phase6/results/regression/`. It never invokes the earlier phase validators that write into frozen directories. Existing regression simulations do not consume encoder outputs.

Validation renders movies one at a time for actual-content deduplication, fits training-only normalization, and writes a freeze lock **before** any validation/test encoder responses. It saves 1,024 encoded NPZs, not raw frame sets, plus frame hashes, mapping, scales, plots, episode metrics, tests and [gate report](results/validation_report.md). No parameter search or validation/test-driven fitting is allowed. Future reruns require identical locked sources, config, normalization, manifest and protected artifact hashes; mismatches are rejected. A lock is local evidence, not external preregistration.

## Frame-only API

```python
import json
from pathlib import Path
from connectome.scripts.phase6.encoder import CausalEncoder, load_config
from connectome.scripts.phase6.dataset import encode_saved

normalization = json.loads(Path("connectome/phase6/results/normalization.json").read_text())
encoder = CausalEncoder(load_config(), normalization)
encoded = encode_saved(encoder, "connectome/phase5/results/samples", "test_looming_1")
# Or encoder.encode(frames, timestamps_s) with the two validated arrays only.
```

`encode_saved` calls the existing Phase 5 `load_stimulus` interface and discards evaluator metadata/config before encoding. Invalid mandatory Phase 5 metadata is rejected by that loader; it is never used to extract encoder features. Benchmark validation uses the existing generator transiently instead of persisting another copy of the frame dataset.

## Output schema 1.0

| Array / field | Contract |
| --- | --- |
| `channels` | float64 `(T,2)`, `[LC4_like,LPLC2_like]`, bounded [0,1], arbitrary dimensionless drive |
| `drive` | float64 `(T,321)`, identical values within each assigned population; DN columns zero |
| `body_ids` | int64 `(321,)`, exact frozen node CSV row ordering, **not sorted numerically**; assignment recorded in `results/mapping.json` |
| `timestamps_s` | float64 `(T,)`, instantaneous frame availability in seconds, strictly increasing, no ms implicit conversion |
| `radius_px`, `area_px`, `valid`, `raw_channels` | Diagnostic arrays in saved NPZ; invalid border-touching/absent objects suppress drive |
| `schema_version`, `encoder_version`, `config_sha256`, `normalization_sha256` | Scalar Unicode arrays, readable with NumPy `allow_pickle=False` |

In-memory output additionally exposes contrast, backward speed and history-anchor diagnostics. `results/encoded_index.json` gives hashes and freeze-lock references for every NPZ. `causal_hold` performs latest-frame-only hold with zero before the first timestamp. It does not invoke the simulator, infer duration, or interpolate future frames. Explicit seconds/ms conversion is the future consumer's responsibility.

## Scientific interpretation

Static and translation rejection, polarity symmetry, clipping suppression and growth responses are consequences of the engineered equations. LC4 velocity/LPLC2 size-selectivity are only qualitative motivations from [Ache et al. (2019)](https://pubmed.ncbi.nlm.nih.gov/30827912/) and [Klapoetke et al. (2017)](https://pmc.ncbi.nlm.nih.gov/articles/PMC7457385/), both already in the Phase 5.5 evidence register. No physiological amplitude, latency, retinotopy or spikes/s calibration is claimed.

Uniform modal-background segmentation assumes a single solid circle occupying less than half the image. It is not general vision and does not implement the biological radial-motion-opponency circuit. Clipping conservatively suppresses drive. Complex scenes, flicker validation, sensory calibration, synthetic spatial mappings, steering and all Phase 7+ work remain unresolved. Frozen-context discrepancies are recorded in the specification. Gate failures must remain reported, not silently tuned away.
