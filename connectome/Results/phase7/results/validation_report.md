# Phase 7 validation report

Session validation UTC: 2026-10-11T11:31:07.446434+00:00. Overall status: **PASS**. 51/51 checks passed; failed checks: [].

Phase 5 schema-1.0 stimuli → frozen Phase 6 encoder → unchanged Phase 4 simulator → frozen Circuit v2. No actions, behavioral metrics, baselines or later-phase implementation. All activity units are arbitrary model units.

## Evidence actually run

- Read-only Phase 1 verification: 33/33 checks. Phase 2: 8/8. Circuit v2 raw-source verification: 48/48. Independent audit: 12/12. Logs and exact commands: `regression/before/summary.json` and `command_1.log` through `command_4.log`. These verify earlier implementations in this session; they are not new biological evidence.
- Earlier unit suites before and after: 49 Phase 4, 114 Phase 5, 44 Phase 5.5 and 52 Phase 6 tests (259 total). Phase 4 integration assertions separately: 159/159 on both runs. All passed. Read-only regression writes solely to Phase 7.
- Phase 7 tests: 41, failures 0, errors 0, skipped 0. Covers exact node order, mapping, matrix direction, dimensions, units, input scaling, irregular/fractional/60 Hz hold, step/state timing against an independent Euler calculation, explicit duration/end boundary, future causality, metadata exclusion, zero contrast, controls and invalid-input rejection. Logs/XML are saved.
- Frozen locks verified: 152 unique locked files; all 1,024 encoded artifact file hashes and manifest identity checked. Dataset isolation summary rechecked against recorded hashes. Full Phase 6 benchmark response gates were **not rerun**; their locked saved evidence was reviewed. Saved normalization retained exactly; no fitting.
- 8 fixed training clips: regenerated actual movie/time hashes match frozen Phase 6 records. Fresh encoding and frozen-encoding replay yield bitwise-identical drive and activity. Independent repeated runs reset state and are bitwise identical. All saved arrays reload exactly with the declared dtypes. Held-out neural simulations: 0.
- 1237 protected earlier files have identical before/after SHA-256 hashes. Inventories include Phase 1–6 artifacts/scripts, Phase 5.5, root README/config/requirements and Phase 1 data alias. Caches excluded. No prior validators that overwrite frozen outputs were invoked.

## Timing, scaling and observed samples

Run duration is explicitly 1,000 ms; the earlier default 500 ms is preserved in its own file. All other simulator settings stay unchanged: gain 0.5, tau 10 ms, Euler dt 1 ms, input_scale 0.4, clip_max 50, zero bias/state/noise, no warmup. Encoder scales remain [8.632185525889524, 8.417362938348457].

Drive is `(60,321)` and state is `(1001,321)`. Step-start inputs are `(1000,321)`. Input is selected at the latest frame timestamp <= simulator time / 1,000. Frame 1 first enters at 17 ms, not 16 ms. Each input updates the following state; the 1 s endpoint is diagnostic only. The final frame is held through the last 999 ms step. Phase 4 applies 0.4 once; DN direct input is exactly zero. No sub-frame sensory or calibrated biological latency claim follows.

| Training sample | Peak activity | Peak scaled input | Activation clipped fraction | Simulator runtime (s) |
| --- | --- | --- | --- | --- |
| train_f0000_looming | 13.153 | 0.302803 | 0 | 0.0179945 |
| train_f0000_static_initial | 0 | 0 | 0 | 0.0175447 |
| train_f0000_static_terminal | 0 | 0 | 0 | 0.0176035 |
| train_f0000_translating_initial | 0 | 0 | 0 | 0.0171072 |
| train_f0001_looming | 13.9063 | 0.275403 | 0 | 0.0176336 |
| train_f0001_static_initial | 0 | 0 | 0 | 0.0172597 |
| train_f0001_static_terminal | 0 | 0 | 0 | 0.0170932 |
| train_f0001_translating_initial | 0 | 0 | 0 | 0.0168038 |

Runtime covers Phase 4 simulation/readout computation only, not loading/encoding/diagnostics. Clipping counts preclip activations above 50 over all step×neuron samples, not just states near the cap; encoder channel caps are recorded separately in `episode_results.json`. Static initial, static terminal and matched translation remain exactly silent; this follows from the engineered encoder plus zero initial state. Nonzero looming activity is an integration result, not evidence of useful escape behavior or a wiring advantage.

## Reproducibility artifacts

Exact invocations, versions and hashes are saved in `validation_results.json`, `run_configuration.json`, resolved configs, episode metadata, tests logs/XML and regression summaries. `stimuli/` holds complete Phase 5 schema file sets and configs; `activity/` holds full states, frame drive, causal step inputs, body IDs, resolved configs and provenance. Two family activity plots and one all-neuron heatmap are in `plots/`. Numerical reruns compare arrays bitwise; timestamps/runtime in metadata are expected to vary.

Run from repository root:

```bash
MPLCONFIGDIR=/tmp/fly-phase7-mpl ./venv/bin/python -m connectome.scripts.phase7.validate_phase7
```

## Conflicts and unresolved issues

Preserved documentation conflicts: root README still describes v1 and outdated hemisphere counts; Phase 3 handoff misidentifies the weight-172 edge as intra-LPLC2 while CSV has LC4 81112 → DNp04 531898; Phase 3 confidence range omits low-confidence DNp01 values; Phase 4 specification describes dictionary input while actual simulator requires the callback used here. The 500 ms default versus 1 s benchmark is resolved solely by explicit episode duration. See `../specification.md` for details; no protocol change was made.

Historical Phase 0 has no separate completion evidence. The referenced progress PDF is missing from this checkout and was not reviewed. Phase 7 does not independently repeat full Phase 6 cohort response evaluation; it verifies frozen evidence, all artifact hashes and selected training replay. No calibrated neural units, biological signs/latencies, receptive fields, general-scene encoder, useful behavioral outcome or control-model comparison has been established. Phases 8+, full benchmark neural runs, webcam and 3D demonstrations remain outside this work. No dependencies added, commit or push performed.

## Delivery checks

The documented standalone `run_pipeline` CLI was executed for `train_f0000_looming`. Every saved array matches the validator activity output bitwise. All three saved plots were visually inspected; labels and traces are readable. Final delivery hash check again confirms all 1,237 protected files unchanged. Machine-readable checks and CLI artifact hash are in `delivery_checks.json`; CLI invocation and environment are in `cli_activity/train_f0000_looming_metadata.json`.
