# Phase 8 completion — version 1.2.0

This is the current Phase 8 completion entry point. The earlier `phase8/README.md` and `phase8/results/` are preserved historical v1.1 partial checkpoints. [Amendment v1.2](amendment_v1_2.md) documents the authorized prerequisites, calibration, independent synthetic mappings and motor-rule assumptions. The current [completion report](results/completion_report.md) records what was actually run.

The primary decoder is calibrated and frozen on train/validation data after integrating feature-only and linear temporal controls. Primary input remains the frozen uniform broadcast and its steering command is deliberately zero. The separately named synthetic spatial condition implements all five predeclared mapping seeds and a causal, latched normalized turn request from bilateral DNp06. It is a working engineered spatial decoder, not measured retinotopy or validated fly steering.

Run from the repository root with existing dependencies:

```bash
# First completion only; before evidence is never overwritten.
./venv/bin/python -m connectome.scripts.phase8.completion.evidence
./venv/bin/python -m connectome.scripts.phase8.completion.regression --stage before
MPLCONFIGDIR=/tmp/fly-phase8-completion-mpl ./venv/bin/python -m connectome.scripts.phase8.completion.validate_completion
```

For numerical reproduction, use the existing before records and run `validate_completion`. Completion outputs are refreshed; earlier-phase and v1.1 checkpoint files remain unchanged. Source/config changes after calibration are rejected. Reproduction must select the same thresholds, linear weights and steering normalizers before replacing a recorded freeze; numerical traces are checked deterministically. Runtime/date evidence may vary.

Decode saved Phase 7 activity with the completed primary model:

```bash
./venv/bin/python -m connectome.scripts.phase8.completion.run_decoder \
  --activity-dir connectome/phase7/results/activity \
  --stimulus-id train_f0000_looming
```

Use `--overwrite` when repeating an existing ID. Outputs stay under `phase8/completion`. `CalibratedDecoder` verifies its freeze, source hashes, prerequisite evidence and earlier frozen pipeline before inference. Complete action NPZ schema 1.2 stores score/persistence/event/latch, ten DN traces, normalized turn command and raw DN imbalance. Action JSON records calibration, spatial condition, and the engineered interpretation. The primary command is unsteered; spatial commands require their recorded mapping and are explicitly not separately validation-calibrated.

Controls share encoded input, gain/scaling conventions and the 20 ms first-event rule. The feature-only combination has no fitted weights; the linear control has two nonnegative fitted coefficients, fixed zero bias and fixed ridge penalty. They are minimal prerequisites, not the later full fair-control experiment. Calibration evaluates all 128 validation scenarios; test-ID/OOD circuit/decision data remain unused.

Synthetic mapping assigns Gaussian fields from identities/type/side and seed only, without connectivity, outcomes or receptive-field fitting. Current-frame centroid localizes the frozen global signal for that secondary condition. Mapping files precede activity. Steering gain normalization uses uniform training-positive DNp06 peaks only, before spatial outcomes. Every seed and both predeclared spatial fixtures are reported; no favorable seed is selected. Uniform primary input cannot recover location, so it is never given an inferred direction.

Phase 8 completion covers the engineered decoder, prerequisites, final initiation calibration and conditional spatial steering implementation. Biological sensory/motor validation, noise robustness, action physics, world geometry, behavioral success, test experiments and remaining shuffled/NN controls are later questions. No Phase 9 environment, dependency install, commit or push is included.
