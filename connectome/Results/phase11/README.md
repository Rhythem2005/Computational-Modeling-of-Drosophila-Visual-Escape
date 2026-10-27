# Phase 11A — controlled training and calibration

The user authorized the saved training plan on 25 October 2026. The original
planning document is retained unchanged as provenance. No scientific design,
encoder normalization, control seed, loss or calibration rule is amended.

All new code is in `connectome/scripts/phase11/`; outputs are in `results/`.
Use the existing Python environment from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 ./venv/bin/python -m connectome.scripts.phase11.launch --task integrity
PYTHONDONTWRITEBYTECODE=1 ./venv/bin/python -m connectome.scripts.phase11.launch --task engineering
PYTHONDONTWRITEBYTECODE=1 ./venv/bin/python -m connectome.scripts.phase11.launch --task profile
PYTHONDONTWRITEBYTECODE=1 ./venv/bin/python -m connectome.scripts.phase11.launch --task primary
PYTHONDONTWRITEBYTECODE=1 ./venv/bin/python -m connectome.scripts.phase11.launch --task secondary
PYTHONDONTWRITEBYTECODE=1 ./venv/bin/python -m connectome.scripts.phase11.launch --task freeze
```

Only proceed when the preceding gate passes. The launcher uses the same verified
legacy file inventory and path translation as Phase 10, without invoking its
output-writing launcher or earlier validators. Original earlier files are hashed
before and after every invocation. Tests run in a second disposable copy.
Gate B locks the tested Phase 11 source hashes; edits require testing again.

The exact ledger has 120 trial identities and 816 calibration identities (936
jobs). No best seed, mapping, shuffle or rewire is chosen. Separate learning-rate
selection is performed for each of ten GRU seeds per mapping. Failed trials are
retained and stop execution; no silent retry/redraw. Interrupted jobs resume the
same identity. Every committed batch checkpoint contains current parameters,
Adam moments/update count, RNG state, shuffled order, batch offset, partial epoch
totals, epoch/history, patience and best weights. Atomic generation pointers and
SHA-256 checks reject torn/tampered/incompatible resumes. Only current and prior
checkpoint generations are retained. Histories and final selected weights persist.

Gate C measures one complete profiling epoch at the frozen settings (16 gradient
batches plus 8 validation batches), actual checkpoint writes, one reference rate
clip, resident memory and output sizes. Profiling weights cannot qualify as
selected models and are stored only under `results/resources/`. A conservative
disk allowance includes uncompressed trace bounds, two output copies and 5 GiB
reserve. Discharging battery capacity below the earliest-stop projected full
schedule blocks Gate D until sustained power is available. Runtime estimates from
one epoch/clip are provisional and exclude spatial preparation and decoding.

Input caches store causal frame drives, not metadata inputs, and include all
384 train/validation clips for each mapping. Test identities are rejected before
file access. Spatial regeneration must reproduce frozen movie hashes and global
encoder outputs, preserving all five independent field assignments. Valid-frame,
channel-cap and rate-activation clipping diagnostics remain visible.

The original episode BCE selects checkpoints and learning rates. Separately saved
decoder diagnostics retain 20 elapsed ms (21 samples), first-event latch, early
alarms, timely TPR, full-episode negative FPR and misses. The endpoint is excluded;
post-horizon late events are unobserved rather than inferred. Candidate assessments
explicitly record eligible finite candidates and sentinel-only feasibility. The
silent sentinel guarantees feasibility for valid scores; the FPR limit is never
relaxed. JSON/reload/decoder tests exercise `5e-324`, exact equality and silence.
Subnormal thresholds are platform-sensitive and have no established noise margin.

Freeze records bind model, source, manifest, input index, calibration and
diagnostic hashes. They do not authorize test execution in this stage. All
training/validation metrics are calibration evidence, not independent performance.
The GRU has 16,241 learned parameters; fixed anatomical weights are not fitted.
This stage cannot establish biological fidelity, a wiring advantage or general
escape competence. No dependencies, commits, pushes or Phase 12+ work are included.

See `results/validation_report.md` for actual gate outcomes and completed counts.
