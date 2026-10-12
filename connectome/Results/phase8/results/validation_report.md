# Phase 8 engineering validation

UTC: 2026-10-11T11:46:51.114500+00:00. Status **PASS**: 30/30 gates passed; failed gates [].

Working causal DNp01 initiation decoder, with the user-approved threshold amendment v1.1. No direction, physical movement, environment, behavioral evaluation or control models were implemented. Threshold is **provisional**, not validation-selected. Final calibration and directional steering remain gated.

## Commands and evidence actually run

- `./venv/bin/python -m connectome.scripts.phase8.evidence`: existing Phase 5.5/6 locks and all 1,024 encoded hashes verified; nine Phase 7 source files, eight saved episode artifact sets, plot hashes, passing report and earlier preservation inventory verified. Earlier full Phase 6 response gates were not recomputed.
- `./venv/bin/python -m connectome.scripts.phase8.regression --stage before`: 300 earlier unit tests and 159 Phase 4 integration assertions passed, writing only Phase 8 evidence.
- Phase 8 tests: 64 passed, 0 failures, 0 errors, 0 skipped. Exact test command/log/XML saved here. Covers mapping, bilateral score, causal 20 ms persistence, equality/drop/pulse cases, first-event latch, future/prefix invariance, endpoint exclusion, candidate-only training provenance, amendment versus original audit, ranking/ties, explicit calibration gate, real saved Phase 7 replay and output round-trip.
- After implementation, all 300 earlier tests and 159 integration assertions passed again, with identical counts/results. `1326` earlier files retained identical before/after SHA-256 hashes. Earlier-output-writing validators were not invoked.
- Materialized all 192 training-negative neural traces (64 complete families), with no failed/excluded run and zero activation clipping. Saved ten-DN, score and sustained-score arrays reload exactly. Trace/config/input/model hashes, runtime and validity are saved per episode. Total materialization time 4.17682 s includes loading, simulation, decoding and storage.
- Replayed eight saved Phase 7 training samples into provisional actions; repeated decoded arrays are bitwise identical, as are saved round-trips. Validation neural runs: 0. Held-out neural/decision runs: 0. No thresholds were selected from these demonstration outcomes.
- The bounded-history streaming minimum equals an independent brute-force reference on 10,000 synthetic samples. Seed/runtime evidence saved in the gate record; it is not a like-for-like speed comparison or a biological result.

## Threshold amendment and observed requests

Original raw quantiles are saved separately in `original_candidate_audit.json`. The approved finite threshold is the next larger float64 after each training-negative quantile. All observed training-negative sustained maxima are zero, so 31 quantile levels collapse to one finite candidate plus the silent sentinel. Provisional highest-quantile threshold: `5e-324`. This tiny value separates numerical silence and is not noise-robust neural calibration.

The protocol's `>=` comparison is retained. Original raw threshold 0 fires after 20 ms on silent traces; the audit records this rather than changing comparison or hiding events. The amended provisional threshold rejects exact silence and emits initiation requests on the two training looming examples. These are engineered training demonstrations, not evidence of held-out accuracy, useful escape or a wiring advantage.

| Training example | Amended provisional first event (ms) | Original raw-quantile audit first event (ms) |
| --- | --- | --- |
| train_f0000_looming | 256.0 | 20.0 |
| train_f0000_static_initial | None | 20.0 |
| train_f0000_static_terminal | None | 20.0 |
| train_f0000_translating_initial | None | 20.0 |
| train_f0001_looming | 272.0 | 20.0 |
| train_f0001_static_initial | None | 20.0 |
| train_f0001_static_terminal | None | 20.0 |
| train_f0001_translating_initial | None | 20.0 |

The score is the mean of DNp01 body IDs 10010 and 10001 in arbitrary model units. A closed 21-sample window at 1 ms dt spans 20 elapsed ms. The first event is one impulse; the request remains latched. Pre-onset events are never reset. A 1 s endpoint state cannot trigger an event. All ten DN traces are saved, but only bilateral DNp01 affects initiation. Steering stays null, explicitly unavailable.

## Reproduction and artifacts

```bash
MPLCONFIGDIR=/tmp/fly-phase8-mpl ./venv/bin/python -m connectome.scripts.phase8.validate_phase8
```

Saved artifacts: implementation/config/amendment lock before training activity; all training trace records and candidate provenance; provisional decoded NPZ/action JSON/metadata; separate original-rule audit; two request plots; tests/regression logs/XML; complete before/after inventories; validation JSON with versions, exact invocations, hashes and gate outcomes. Earlier phase files, normalization and dynamics are unchanged. No new dependencies, commit or push.

## Gates and unresolved issues

The Phase 6 handoff requires feature-only and linear temporal controls before final decoder tuning. They are absent. Phase 8 therefore does not fit a final validation-selected threshold or claim a completed calibrated primary model; production code explicitly rejects final-calibrated status. The future validation rule remains highest timely TPR under full-episode FPR<=0.05, ties smaller FPR then higher threshold, with the always-silent sentinel. It was tested only on synthetic ranking fixtures here.

Spatial mapping is absent, so directional steering cannot be grounded in the existing global input; DN side differences and secondary populations are exploratory activity only. No calibrated activity/latency, noise robustness, physical jump/motor plant, danger or collision label, closed-loop escape, baseline comparison, H1/H2 outcome or biological fidelity is established. The numerical one-float margin may be inadequate once noise/spontaneous drive is introduced. Phase 9+ work remains unauthorized. Missing historical Phase 0 evidence and the earlier progress PDF remain unresolved. Earlier documentation conflicts are preserved in the Phase 7 specification. The approved amendment is separately versioned; parent protocol files were not edited.

## Delivery checks

The documented standalone `run_decoder` CLI was executed on the saved Phase 7 `train_f0000_looming` activity. Every NPZ array matches the validator output bitwise, and action JSON matches exactly. Both saved request plots were visually inspected. Final delivery hashing confirms all 1,326 protected earlier files unchanged. Evidence is in `delivery_checks.json`, with invocation/environment in the CLI metadata.
