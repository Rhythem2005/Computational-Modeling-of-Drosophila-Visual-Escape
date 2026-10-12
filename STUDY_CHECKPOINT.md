# FLY study checkpoint — 11 October 2026

User decision: stop implementation after Phase 9 and study the completed phases first. Do not start Phase 10 or later without renewed authorization. This file is the durable handoff for future sessions; detailed saved reports remain authoritative. Creating this checkpoint did not rerun validators or experiments.

## Scientific purpose and boundary

Study whether a circuit extracted from the male Drosophila CNS connectome supports useful visual escape behavior compared with fair controls. Connectivity is anatomical data; encoding, dynamics, motor mappings and environment rules are engineered. We have not established biological fidelity, useful general behavior or a connectivity advantage. No living brain or complete brain reproduction is involved.

## Phase record and reading order

| Phase | Saved implementation/evidence and study focus |
| --- | --- |
| 0 | Historical completion was reported, but separate completion evidence remains missing. Do not treat it as independently verified. |
| 1 | Connectivity processing and matrix construction. Phase 7 recorded 33/33 read-only checks. Current user cleanup removed six legacy files and their data aliases; exact archived bytes were verified only in the Phase 9 execution snapshot. |
| 2 | Candidate circuit selection: `connectome/phase2/phase2_report.md`. Phase 7 recorded 8/8 read-only checks. |
| 3 | Frozen Circuit v2: 321 neurons, 11,557 directed edges, 91,023 synapses. Read `connectome/phase3/circuit_v2_specification.md`, `validation_report.md`, and `phase3_final_audit_report.md`. Phase 7 recorded 48/48 source checks and 12/12 independent audit checks. |
| 4 | Neural simulator: `connectome/phase4/specification.md` and `phase4_validation_report.md`. Frozen model uses Euler dt 1 ms, tau 10 ms, gain 0.5, input scale 0.4, cap 50, zero initial state/bias/noise; activity has arbitrary model units. |
| 5 | Static, translating and looming stimuli: `connectome/phase5/specification.md`, `README.md`, and `phase5_validation_report.md`. |
| 5.5 | Research boundaries and benchmark partitions: `connectome/phase5_5/research_protocol.md`, `benchmark_design.yaml`, `evidence_register.md`, `phase6_handoff.md`, and `results/validation_report.md`. Original primary task is open-loop expansion discrimination. |
| 6 | Frozen causal frame-only encoder: `connectome/phase6/specification.md`, `README.md`, `results/normalization.json`, and `results/validation_report.md`. Uniform population broadcast is primary; descending neurons receive zero direct visual input. Normalization was preserved, not refitted in later phases. |
| 7 | Stimulus → encoder → simulator integration: `connectome/phase7/specification.md`, `README.md`, and `results/validation_report.md`. 51/51 validation checks; 41 integration tests; 259 earlier tests and 159 separate simulator assertions passed. Eight training clips replayed bitwise; 1,237 earlier files preserved. Frame at 1/60 s becomes available at 17 ms; drive is held causally and scaling applies once. No held-out neural runs. |
| 8 | Completed decoder version 1.2: read `connectome/phase8/completion/README.md` and its `results/delivery_verification.json`, rather than interpreting the historical root v1.1 report as the final status. 382 unique tests plus 159 simulator assertions; two exact completion validator runs. Frozen calibration hash: `73ba74974eeda1070e529a761588259a31bef0c4fb403efc0c71e6ec1cda6a41`. |
| 9 | Completed engineering environment: `connectome/phase9/plan.md`, `research_notes.md`, `protocol.md`, `environment_config.yaml`, `README.md`, `results/validation_report.md`, and `results/delivery_verification.json`. 410 unique tests plus 159 simulator assertions; two successful full validators; 15 fixed episodes numerically reproduced and repeated bitwise. This is an engineering completion, not a confirmatory behavioral experiment. |

Counts are recorded results from earlier work in this conversation, not new runs during checkpoint creation. Later suites include earlier tests; do not add their totals as independent tests or trials.

## Key Phase 8 results

- DNp01 mean activity supplies the primary score. Detection requires a closed 20 ms interval (21 samples at 1 ms) using ≥ and latches the first event; the 1,000 ms endpoint is excluded.
- User-approved, separately versioned threshold amendment places thresholds just above training-negative quantiles. The selected threshold for all three calibration models is 5e-324. Validation: 32 positives and 96 negatives, timely TPR 1 and FPR 0 for all three models. These are calibration results, not untouched-test performance.
- Minimal feature-only and linear prerequisites were completed; they do not replace Phase 10 fair controls. The fitted linear weights are [0, 3.5686234819095057], bias 0.
- Synthetic steering uses five independent field seeds 55010–55014 and frozen DNp06 gains [3.3915051594691583, 2.678174077738024]. Its primary threshold is reused without separate spatial calibration. Uniform primary input yields zero steering.
- No held-out benchmark neural/decision runs or biological receptive-field/motor validation were performed.

## Key Phase 9 results

- Separate protocol `fly_closed_loop_engineering_v1`: 1,000 ms horizon, 1 ms world step, 60 Hz stabilized camera, swept disk collision, 20 ms motor delay, one-shot latched translation, and explicit collision/survival/latency/false-alarm metrics.
- Five fixed primary fixtures and ten synthetic left/right fixtures across five seeds. Dangerous primary and synthetic fixtures requested escape at 239 ms; first displacement occurred at 260 ms. All dangerous fixtures met the engineered success rule. Static input caused no request. The expanding noncolliding near-miss caused a false alarm.
- Action changes later visual frames; the scripted coupling check verifies this plumbing. It is not a comparative controller experiment.
- Spatial encoder valid-frame fractions ranged from 71.7% to 100%; edge clipping remains an observed limitation.
- 2,139 current-workspace parent files and 2,151 frozen execution-snapshot parent files were preserved. One development failure was fixed by converting the loader's body-ID list to the exact frozen int64 order; physical parameters were not tuned. The failed evidence and repair record remain saved.
- Plots: `connectome/phase9/results/plots/primary_world_activity.png`, `action_visual_coupling.png`, and `synthetic_escape_paths.png`.

## Reproduction and checkout caveat

The user switched to `phase6-main-push` and updated the root README while later work was in progress. Missing Phase 7/8 and planning files were recovered byte-for-byte from the local stash without popping it or reverting user changes. Old strict preservation inventories conflict with the current README and missing legacy Phase 1 paths. Phase 9 therefore uses a documented isolated execution copy with verified archival bytes; only Phase 9 outputs return to this checkout. See `connectome/phase9/recovery_record.json`, `execution_baseline/README.md`, and `results/execution_snapshot.json`.

When reproduction is needed, use the launcher, not earlier output-overwriting validators:

```bash
MPLCONFIGDIR=/tmp/fly-phase9-mpl ./venv/bin/python -m connectome.scripts.phase9.launch --task validate
```

Read and verify existing evidence before rerunning; validation updates Phase 9 outputs. Preserve all earlier phase files, frozen configs, normalization, protocol and held-out partitions. No new dependencies without approval, no commit or push. Phase 7/8/9 files remain untracked in the current Git checkout; this checkpoint does not commit them.

## Unresolved issues to study

- World-domain and separate spatial threshold calibration remain absent; the one-float silence threshold has no established noise robustness.
- Near-miss false alarms and clipped-frame encoder validity require later investigation.
- Latched actions provide feedback-coupled sensing, but no ongoing adaptive steering/navigation.
- Camera, synthetic fields and motor plant are assumptions, not measured fly biomechanics. Fixed fixture success does not establish useful general behavior, wiring advantage or H1/H2.
- Earlier preserved documentation discrepancies include the Phase 3 weight-172 edge attribution and confidence range, and the Phase 4 dictionary-versus-callback interface. Details are in `connectome/phase7/specification.md`; these were not silently revised.
- Phase 0 historical evidence and the referenced progress PDF `output/pdf/FLY_Project_Progress_Through_Phase_6.pdf` were absent when audited. Current root compatibility caveats remain.

## Resume boundary

Study in order: anatomy/selection (1–3), dynamics (4), stimuli (5), protocol (5.5), encoding (6), timing/integration (7), decision/steering (8), environment/metrics and limitations (9). After study, ask for authorization before Phase 10 fair controls. Phases 11–14 and optional webcam/3D demonstrations remain future work.
