# Phase 8 completion validation — v1.2.0

Status: **PASS / COMPLETE_ENGINEERING**. UTC: 2026-10-11T16:40:02.683098+00:00. Current implementation: `connectome/scripts/phase8/completion/`. Historical v1.1 partial checkpoint and parent protocol files remain unchanged. The separate amendment and condition definition were saved before new validation/spatial outcomes.

## Completed deliverables

Primary bilateral DNp01 initiation is now validation-selected and frozen after integrating the required feature-only and linear temporal controls. The zero-threshold amendment uses `nextafter(negative quantile,+infinity)` and retains the causal 20 ms `>=` rule. The optimized bounded-history decoder, first-event latch and endpoint exclusion remain unchanged. Primary uniform input has an explicit neutral turn command. The separately named synthetic spatial condition supplies all five independent field mappings and a DNp06 gain-normalized, bounded, latched turn request. It is an engineered motor convention; no measured retinotopy or physiological steering claim is made.

## Evidence actually run

- Verified prior saved phase/protocol/encoder/pipeline locks and v1.1 checkpoint before relying on them. All earlier encoded-file hashes were checked read-only; no earlier validator regenerated outputs.
- Completion tests: **18 passed**, zero failures/errors/skips. Earlier regressions before and after: **364 tests and 159 Phase 4 integration assertions passed**, unchanged counts. Logs/XML and exact commands are saved here.
- Reused 192 verified v1.1 train-negative neural traces; these were not fresh neural simulations in this session. Newly simulated all 64 training positives and all 128 validation scenarios with frozen Phase 7/4/6 interfaces. Every model received the same full 321-neuron encoded vectors; DN direct input remained zero. All neural calibration runs were finite with no activation clipping; no scenario failed or was excluded.
- Linear weights fitted once on the 256 training clips only: `[0.0, 3.5686234819095057]`; zero bias, two coefficients, fixed ridge 1e-6, no hyperparameter search. Temporal Euler filter uses dt=1 ms, tau=10 ms, scale=0.4 and zero initial state. Feature-only channel mean is fixed, with no trained coefficients. These are minimal calibration prerequisites; comprehensive fair-control experiments remain later work.
- Generated training-negative candidate plans for all three models before validation selection. All 128 validation clips were used only for the specified threshold ranking, with 32 positives and 96 negatives. First events before 200 ms are retained as early decisions, not reset; negative FPR uses the full episode. No test-ID/OOD neural or decision run occurred.
- Saved/froze thresholds, weights, train/validation identities, all 384 score/DN traces, full candidate assessments/predictions, control proof and source/config/parent/artifact hashes. Replayed eight saved Phase 7 training examples into final primary action schema 1.2, with bitwise repeat checks and neutral steering. Ran the completed CLI on `train_f0000_looming`; its arrays/action equal the integrated decoder. All saved action arrays/dtypes and JSON round-trip exactly.
- Saved every synthetic field assignment before outcomes. Ran both predefined spatial looming fixtures for each of five seeds, then repeated all ten simulations bitwise. Saved stimuli/configs, full activity/drive/centroid arrays, actions and metadata. All spatial runs were finite, unclipped, DN input zero and turn requests bounded. No seed, width or directional rule was selected from results.
- **1606 earlier phase/checkpoint files have identical before/after SHA-256 hashes.** No dependency install, commit, push, environment physics or Phase 9 implementation.

## Validation calibration results

| Model | Frozen threshold | Timely validation TPR | Full-episode negative FPR |
| --- | --- | --- | --- |
| circuit | {'kind': 'finite', 'value': 5e-324} | 1 | 0 |
| feature_only | {'kind': 'finite', 'value': 5e-324} | 1 | 0 |
| linear_temporal | {'kind': 'finite', 'value': 5e-324} | 1 | 0 |

These are threshold-selection metrics on validation data, not untouched-test results or evidence of a circuit advantage. All negative sustained maxima were zero; finite candidates collapse to a one-float margin above silence. This is not noise-robust calibration. Spontaneous activity/noise would require a new documented condition and appropriate calibration.

## Synthetic steering integration results

DNp06 bodies 10228/10584 use train-only mean positive-peak normalizers `[3.3915051594691583, 2.678174077738024]`. At initiation, positive normalized left-minus-right imbalance requests a rightward turn. Primary uniform input stays at zero. Spatial initiation reuses the primary frozen threshold solely as an explicitly uncalibrated integration-fixture value; it is not a separately calibrated spatial model.

| Mapping seed | Fixture side | First request (ms) | Latched normalized turn |
| --- | --- | --- | --- |
| 55010 | left | 272.0 | 0.748944 |
| 55010 | right | 272.0 | -0.917303 |
| 55011 | left | 272.0 | 0.765273 |
| 55011 | right | 272.0 | -0.855746 |
| 55012 | left | 272.0 | 0.77251 |
| 55012 | right | 272.0 | -0.888072 |
| 55013 | left | 272.0 | 0.813631 |
| 55013 | right | 272.0 | -0.802758 |
| 55014 | left | 272.0 | 0.834281 |
| 55014 | right | 272.0 | -0.788562 |

These outputs demonstrate implemented commands under independent synthetic sensory/motor assumptions. They do not measure useful escape, anatomical directional fidelity or biological superiority. Both positions reuse the same stimulus geometry across seeds intentionally, to vary mapping alone. No motor plant, heading, collision, speed or success evaluator is present.

## Reproduction and remaining scientific issues

Run `MPLCONFIGDIR=/tmp/fly-phase8-completion-mpl ./venv/bin/python -m connectome.scripts.phase8.completion.validate_completion`. Saved source/config/evidence changes are rejected. Reproduction checks numerical arrays, selections, linear weights, steering scales and freeze against saved results; runtime/date evidence may vary. The CLI in the completion README decodes existing Phase 7 activity and verifies the freeze before inference. Plots are under `plots/`: calibrated scores, all field assignments and all turn traces.

Unresolved scientific issues: biological retinotopy and DN motor interpretation are assumed; tiny silence thresholds lack noise robustness; spatial condition lacks its own final validation calibration; no useful-behavior, held-out-test or fair wiring advantage result is established. Later phases must address behavior, richer controls and repeated experiments. Historical missing Phase 0 evidence/progress PDF and previously documented specification conflicts remain unresolved; this completion does not revise them. The engineering deliverables of Phase 8 are complete within the separately documented v1.2 condition. No later phase was started.

## Final delivery audit

The full completion validator was run twice in this session. The second invocation passed strict saved-result comparisons for all calibration/spatial/action traces, selections, weights, steering normalizers and the calibration freeze. Plots were visually inspected. The final read-only check verified all 13 source hashes, 401 prerequisite artifact hashes and 1,606 protected earlier files. Details and actual invocation counts are in `delivery_verification.json`; deterministic reruns are not independent experimental trials.

Preserved document/interface discrepancies are detailed in [the Phase 7 specification](../../../phase7/specification.md): archival v1/hemisphere counts in the root README; the incorrectly described weight-172 edge (actual LC4 81112 → DNp04 531898); omitted low-confidence DNp01 values; and the dictionary/callback simulator interface description. The preserved v1.1 Phase 8 reports describe the historical partial checkpoint; this v1.2 completion report is the current result. Parent protocol files were not silently revised.
