# Phase 10 — fair control model engineering

Read [plan](plan.md), [specification and fairness rules](specification.md), [research notes](research_notes.md), and the generated [validation report](results/validation_report.md). The unchanged Phase 5.5 open-loop protocol governs these controls. Phase 9 world results do not establish a separately calibrated behavioral benchmark for these architectures.

From the repository root, using the existing environment:

```bash
./venv/bin/python -m connectome.scripts.phase10.launch --task preflight
./venv/bin/python -m connectome.scripts.phase10.launch --task validate
```

The launcher handles the user's move of artifacts into `connectome/Results/` by making a byte-verified legacy execution copy, including the already documented archival README and Phase 1 aliases. It never changes earlier source paths, locks, parent results or user Git state. Earlier tests run in their own disposable copies because some write test fixtures into earlier result directories. Only Phase 10 results return here. No original validator is invoked. Failed runs retain diagnostic evidence. The initial workspace inventory is immutable, so later parent changes need review and a new Phase 10 version rather than silently resetting the baseline.

Delivered artifacts include all 30 primary weight-null matrices, 30 secondary degree-null matrices, population-average and reference; native and stability-matched gain records; block invariants and chain diagnostics; ten **untrained** GRU initializations; all ten seeds/two rates exercised on tiny **synthetic-only** training fixtures; and an unexecuted benchmark job plan. The GRU, Adam/BPTT training, stopping/rate selection, lazy train/validation loading, model forward adapters, threshold calibration, artifact/freeze checks and failure contracts are implemented. Minimal feature/linear equations are reused and checked against Phase 8. No test-authorizing scientific model freeze is made from a smoke run.

Programmatic APIs (run inside the launcher's recorded execution snapshot, with the same venv Python):

- `networks.build_bank`, `load_network`, `weight_shuffle`, `population_average`, `rewire`, `stability`.
- `data.TrainingDataset(pipeline).records('train'/'validation')` returns lazy exact-manifest records. Test cohorts are rejected before file access. `step_drive` handles primary frozen encodings; `hold_spatial_drive` accepts frozen independent spatial vectors in the same body-ID order.
- `models.score_model` accepts only input arrays and model state, never labels/metadata/geometry. `rate_trace` retains full states, DN traces and scale/clipping/runtime diagnostics. `minimal_features` supplies identical primary feature-only/leaky features and a shared-population spatial reduction.
- `gru.train_seed` runs both predeclared rates and selects by validation BCE. `save_gru`/`load_gru` serialize checkpoint weights and metadata; output IDs are path-validated. `train_run` exposes single-trial state and epoch/gradient diagnostics. Defaults enforce complete frozen training/validation coverage; synthetic-only tests explicitly set `smoke=True`.
- `calibration.calibrate` applies the unchanged candidate/decision/ranking rule independently per architecture/seed/gain/mapping. `save_freeze` binds calibration, fitted artifacts, source/config and manifest hashes; `load_freeze` rejects tampering. Smoke calibration cannot create a test-authorizing freeze. Actual benchmark fitting/freezing is Phase 11 work.

Null validity, rigidity, mixing limitations, stability failures, fitting opportunities and scale differences are explicit; no architecture is silently redrawn or tuned by held-out outcomes. The job plan covers all six mappings without selecting a best seed. Neural predictions/decisions for test-ID/OOD cohorts, comparative benchmark trials, confidence intervals and H1/H2/H3 conclusions are outside this phase. Earlier evidence hashes include previously generated encoded test files solely for integrity verification; no new held-out inference is performed.

Phase 11 readiness means the software is built and verified. It does **not** mean the benchmark GRUs have already been trained, that all architectures have been threshold-calibrated, or that scientific test results exist. Phase 11 must execute the fixed train/validation plan and freeze models before any untouched test evaluation. Synthetic mappings, the near-zero silence threshold/noise sensitivity, encoder clipping and the abstract motor/world assumptions retain their earlier limitations.
