# Phase 10 validation report

Status: **PASS — COMPLETE_ENGINEERING**, version 1.0.0. UTC: 2026-10-24T19:12:33.260377+00:00.

Frozen Phase 6–9 evidence passed before construction. All 2295 earlier execution-copy files were identical before/after; the outer launcher's workspace inventories independently protect the actual renamed repository. Sources/configuration/seed schedule were saved before engineering outcomes. No earlier validator overwrote frozen results.

Built 62 rate architectures: reference, population average, 30 weight shuffles and 30 degree rewirings, with 124 native/stability-matched condition records. All graph constraints and mixing gates passed; no failures were silently redrawn. All 124 conditions ran on the same synthetic engineering input and saved score/DN traces, final states and scale/clipping/stability/runtime diagnostics. These are plumbing checks, not benchmark comparisons. See `network_bank.json`, `networks/`, `engineering/` and `seed_schedule.json`.

Phase 10: 89 tests, zero failures/errors/skips. Unchanged earlier suites: 410 tests before and after, plus 159 passing Phase 4 integration assertions per run. Unique unit/integration test cases: 499; simulator assertions counted separately. Analytical GRU/BPTT gradients passed independent central finite differences across every parameter in a small model. Adam matched an independent two-update calculation. Tests cover causality/state alignment, training-only gradients, stopping/selection, split/family/identity guards, calibration/event semantics, serialization, tamper detection and all five synthetic spatial mappings.

Saved ten explicitly **untrained** 16-unit GRUs (16,241 parameters each); all ten seeds and both learning rates executed only on tiny synthetic fixtures, with checkpoint roundtrips. No real benchmark GRU training, null-vs-circuit benchmark trials or held-out inference ran. The benchmark job plan has 744 planned rate-model conditions across six mappings, 60 planned two-rate NN searches, and 12 minimal-control conditions. It was not executed. Production fitting/calibration require exact complete training/validation coverage. Synthetic-only calibration cannot authorize test use.

The reference adapter reproduced the frozen pipeline exactly on one previously used training encoding; minimal primary features reproduced Phase 8 exactly. Integrity verification hashes earlier encoded test artifacts but does not run models/decoders on them.

Successful complete validation invocations saved so far: 2. Each reproduction checks existing numerical artifacts rather than overwriting differing results. Exact commands, environment, JUnit/logs, source lock and both regression runs are saved alongside this report.

## Limitations and Phase 11 readiness

Software and reproducible control artifacts are ready. Phase 11 must still execute the predeclared full train/validation fits and per-model/mapping/gain calibration, freeze selected weights/thresholds, and only then run comparative untouched-test experiments. No benchmark performance is established here. Finite rewiring/overlap diagnostics are not a mixing theorem; rigid blocks are explicit. The GRU has larger fitting opportunities, not equal learned parameter capacity. The original synthetic sensory/motor assumptions, noise/near-zero-threshold sensitivity, encoder clipping and uncalibrated world domain remain. No circuit advantage, biological fidelity or hypothesis result is inferred.
