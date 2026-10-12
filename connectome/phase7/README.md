# Phase 7 — frozen visual-to-neural integration

This phase connects Phase 5 schema-1.0 frames to the unchanged Phase 6 encoder and the unchanged Phase 4 simulator on frozen Circuit v2. It saves modeled activity, never actions or behavioral scores. Read [specification.md](specification.md) for timing, units, output schema, preserved discrepancies and limitations. Session evidence is in [results/validation_report.md](results/validation_report.md).

From repository root, use the existing virtual environment:

```bash
# First implementation only: refuses to replace an existing before snapshot.
./venv/bin/python -m connectome.scripts.phase7.evidence
./venv/bin/python -m connectome.scripts.phase7.regression --stage before
./venv/bin/python -m pytest connectome/phase7/tests/ -q
MPLCONFIGDIR=/tmp/fly-phase7-mpl ./venv/bin/python -m connectome.scripts.phase7.validate_phase7
```

The validator reruns Phase 7 tests and earlier regression suites, generates the eight fixed training samples into Phase 7 only, compares fresh encoding with saved frozen encoding, reruns activity bitwise, checks saved arrays, plots activity, and records before/after hashes. It refreshes Phase 7 validation outputs; it never calls the frozen-output-writing validators of earlier phases or fits normalization. To reproduce in this checkout, run the validator using its existing before evidence. To run on another checkout, first create its own before evidence and regression records.

Run an existing Phase 5 saved sample:

```bash
./venv/bin/python -m connectome.scripts.phase7.run_pipeline \
  --stimulus-dir connectome/phase7/results/stimuli \
  --stimulus-id train_f0000_looming \
  --out-dir connectome/phase7/results/cli_activity
```

Existing activity IDs require `--overwrite`. All activity output must stay under `connectome/phase7`. The loader reads complete Phase 5 NPZ/metadata/config file sets; Phase 7 rejects legacy versionless movies. Sample IDs select training data before activity inspection; no held-out simulation or tuning is performed.

```python
from connectome.scripts.phase7.pipeline import FrozenPipeline

pipeline = FrozenPipeline()  # verifies frozen artifacts; no fitting
run = pipeline.run_saved("connectome/phase7/results/stimuli", "train_f0000_looming")
# Or: run = pipeline.run_frames(frames_uint8, timestamps_float64_s, duration_ms=1000.0)
# Or: run = pipeline.run_encoded(pipeline.load_frozen_encoded("train_f0000_looming"), 1000.0)
print(run.states.shape)  # (1001, 321), initial and endpoint states included
```

Inputs are available only at each frame timestamp, then causally held. Phase 4 samples input at each step start and applies scale 0.4 once; the resulting state is timestamped one step later. State includes the diagnostic 1 s endpoint; step input ends at 999 ms. Every episode resets to zero, with no warmup. Duration comes explicitly from the stimulus, since the last frame timestamp does not specify the end. Units are arbitrary drive and modeled activity, not spikes/s.

The protocol remains unchanged. The reported differences between old documentation and actual interfaces are preserved in the specification. Full behavioral experiments, controls, biological calibration, Phase 0 historical certification and the missing progress PDF remain unresolved. No dependency was added, and no commit or push is part of this workflow.
