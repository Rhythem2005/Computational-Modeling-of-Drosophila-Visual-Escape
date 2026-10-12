# Phase 6 standalone validation

UTC: 2026-10-11T10:37:42.370914+00:00. Overall gate status: **PASS**.

Encoder 1.0.0 uses frame-only engineered expansion channels. Training-only normalization: 256 clips, zero parameter-search trials. Freeze precedes validation/test response computation; all test results are post-freeze. No circuit integration, decisions or behavioral conclusions.

## Executed commands

- `./venv/bin/python -m connectome.scripts.phase6.regression`: results in `regression/summary.json` (Phase 4 unit tests and integration assertions reported separately).
- `./venv/bin/python -m connectome.scripts.phase6.validate_phase6`: 52 Phase 6 tests, 0 failures, 0 errors, 0 skipped; 1,024 movie hashes and encoded episodes, six diagnostic plots, stable Phase 5 loader exercised. Full logs/XML saved here.
- `143` protected Phase 3/4/5/5.5 file hashes unchanged; bytecode caches excluded. Source/config/normalization/mapping hashes saved in `freeze_lock.json`.

## Gate outcomes

The test suite checks zero contrast, exact polarity symmetry, clipping suppression, reproducibility, metadata rejection/invariance, prefix/future causality, fractional timestamps, seconds/ms availability, invalid inputs and training-only fitting. Benchmark separation/onset/geometry gates are measured below. All cutoffs were recorded before response inspection.

| Gate | Cohort | Channel | Observed | Predeclared threshold | Result |
| --- | --- | --- | --- | --- | --- |
| output_contract | all | both | 0 | 0 invalid episodes | PASS |
| radius_geometry | all | both | 1 | >=0.95 frames within 1 pixel | PASS |
| speed_geometry_median | all | both | 0.0217707 | <=0.20 relative error | PASS |
| speed_geometry_p95 | all | both | 0.133264 | <=0.50 relative error | PASS |
| pre_onset | all | both | 0 | 0 nonzero samples | PASS |
| static_initial | test_id | both | 0 | <=0.01 peak | PASS |
| static_terminal | test_id | both | 0 | <=0.01 peak | PASS |
| translating_initial | test_id | both | 0 | <=0.01 peak | PASS |
| loom_response | test_id | LC4_like | 1 | >=0.95 fraction with peak>0.01 | PASS |
| loom_response | test_id | LPLC2_like | 1 | >=0.95 fraction with peak>0.01 | PASS |
| onset_latency | test_id | both | 1 | >=0.95 begin in [0.2,0.38] s | PASS |
| static_initial_polarity_-1 | test_id | both | 0 | <=0.01 peak | PASS |
| static_terminal_polarity_-1 | test_id | both | 0 | <=0.01 peak | PASS |
| translating_initial_polarity_-1 | test_id | both | 0 | <=0.01 peak | PASS |
| loom_response_polarity_-1 | test_id | LC4_like | 1 | >=0.95 fraction with peak>0.01 | PASS |
| loom_response_polarity_-1 | test_id | LPLC2_like | 1 | >=0.95 fraction with peak>0.01 | PASS |
| onset_latency_polarity_-1 | test_id | both | 1 | >=0.95 begin in [0.2,0.38] s | PASS |
| static_initial_polarity_1 | test_id | both | 0 | <=0.01 peak | PASS |
| static_terminal_polarity_1 | test_id | both | 0 | <=0.01 peak | PASS |
| translating_initial_polarity_1 | test_id | both | 0 | <=0.01 peak | PASS |
| loom_response_polarity_1 | test_id | LC4_like | 1 | >=0.95 fraction with peak>0.01 | PASS |
| loom_response_polarity_1 | test_id | LPLC2_like | 1 | >=0.95 fraction with peak>0.01 | PASS |
| onset_latency_polarity_1 | test_id | both | 1 | >=0.95 begin in [0.2,0.38] s | PASS |
| static_initial | test_ood_contrast | both | 0 | <=0.01 peak | PASS |
| static_terminal | test_ood_contrast | both | 0 | <=0.01 peak | PASS |
| translating_initial | test_ood_contrast | both | 0 | <=0.01 peak | PASS |
| loom_response | test_ood_contrast | LC4_like | 1 | >=0.9 fraction with peak>0.005 | PASS |
| loom_response | test_ood_contrast | LPLC2_like | 1 | >=0.9 fraction with peak>0.005 | PASS |
| onset_latency | test_ood_contrast | both | 1 | >=0.95 begin in [0.2,0.38] s | PASS |
| static_initial_polarity_-1 | test_ood_contrast | both | 0 | <=0.01 peak | PASS |
| static_terminal_polarity_-1 | test_ood_contrast | both | 0 | <=0.01 peak | PASS |
| translating_initial_polarity_-1 | test_ood_contrast | both | 0 | <=0.01 peak | PASS |
| loom_response_polarity_-1 | test_ood_contrast | LC4_like | 1 | >=0.9 fraction with peak>0.005 | PASS |
| loom_response_polarity_-1 | test_ood_contrast | LPLC2_like | 1 | >=0.9 fraction with peak>0.005 | PASS |
| onset_latency_polarity_-1 | test_ood_contrast | both | 1 | >=0.95 begin in [0.2,0.38] s | PASS |
| static_initial_polarity_1 | test_ood_contrast | both | 0 | <=0.01 peak | PASS |
| static_terminal_polarity_1 | test_ood_contrast | both | 0 | <=0.01 peak | PASS |
| translating_initial_polarity_1 | test_ood_contrast | both | 0 | <=0.01 peak | PASS |
| loom_response_polarity_1 | test_ood_contrast | LC4_like | 1 | >=0.9 fraction with peak>0.005 | PASS |
| loom_response_polarity_1 | test_ood_contrast | LPLC2_like | 1 | >=0.9 fraction with peak>0.005 | PASS |
| onset_latency_polarity_1 | test_ood_contrast | both | 1 | >=0.95 begin in [0.2,0.38] s | PASS |
| static_initial | test_ood_growth | both | 0 | <=0.01 peak | PASS |
| static_terminal | test_ood_growth | both | 0 | <=0.01 peak | PASS |
| translating_initial | test_ood_growth | both | 0 | <=0.01 peak | PASS |
| loom_response | test_ood_growth | LC4_like | 1 | >=0.95 fraction with peak>0.01 | PASS |
| loom_response | test_ood_growth | LPLC2_like | 1 | >=0.95 fraction with peak>0.01 | PASS |
| onset_latency | test_ood_growth | both | 1 | >=0.95 begin in [0.2,0.38] s | PASS |
| static_initial_polarity_-1 | test_ood_growth | both | 0 | <=0.01 peak | PASS |
| static_terminal_polarity_-1 | test_ood_growth | both | 0 | <=0.01 peak | PASS |
| translating_initial_polarity_-1 | test_ood_growth | both | 0 | <=0.01 peak | PASS |
| loom_response_polarity_-1 | test_ood_growth | LC4_like | 1 | >=0.95 fraction with peak>0.01 | PASS |
| loom_response_polarity_-1 | test_ood_growth | LPLC2_like | 1 | >=0.95 fraction with peak>0.01 | PASS |
| onset_latency_polarity_-1 | test_ood_growth | both | 1 | >=0.95 begin in [0.2,0.38] s | PASS |
| static_initial_polarity_1 | test_ood_growth | both | 0 | <=0.01 peak | PASS |
| static_terminal_polarity_1 | test_ood_growth | both | 0 | <=0.01 peak | PASS |
| translating_initial_polarity_1 | test_ood_growth | both | 0 | <=0.01 peak | PASS |
| loom_response_polarity_1 | test_ood_growth | LC4_like | 1 | >=0.95 fraction with peak>0.01 | PASS |
| loom_response_polarity_1 | test_ood_growth | LPLC2_like | 1 | >=0.95 fraction with peak>0.01 | PASS |
| onset_latency_polarity_1 | test_ood_growth | both | 1 | >=0.95 begin in [0.2,0.38] s | PASS |
| static_initial | test_ood_size | both | 0 | <=0.01 peak | PASS |
| static_terminal | test_ood_size | both | 0 | <=0.01 peak | PASS |
| translating_initial | test_ood_size | both | 0 | <=0.01 peak | PASS |
| loom_response | test_ood_size | LC4_like | 1 | >=0.95 fraction with peak>0.01 | PASS |
| loom_response | test_ood_size | LPLC2_like | 1 | >=0.95 fraction with peak>0.01 | PASS |
| onset_latency | test_ood_size | both | 1 | >=0.95 begin in [0.2,0.38] s | PASS |
| static_initial_polarity_-1 | test_ood_size | both | 0 | <=0.01 peak | PASS |
| static_terminal_polarity_-1 | test_ood_size | both | 0 | <=0.01 peak | PASS |
| translating_initial_polarity_-1 | test_ood_size | both | 0 | <=0.01 peak | PASS |
| loom_response_polarity_-1 | test_ood_size | LC4_like | 1 | >=0.95 fraction with peak>0.01 | PASS |
| loom_response_polarity_-1 | test_ood_size | LPLC2_like | 1 | >=0.95 fraction with peak>0.01 | PASS |
| onset_latency_polarity_-1 | test_ood_size | both | 1 | >=0.95 begin in [0.2,0.38] s | PASS |
| static_initial_polarity_1 | test_ood_size | both | 0 | <=0.01 peak | PASS |
| static_terminal_polarity_1 | test_ood_size | both | 0 | <=0.01 peak | PASS |
| translating_initial_polarity_1 | test_ood_size | both | 0 | <=0.01 peak | PASS |
| loom_response_polarity_1 | test_ood_size | LC4_like | 1 | >=0.95 fraction with peak>0.01 | PASS |
| loom_response_polarity_1 | test_ood_size | LPLC2_like | 1 | >=0.95 fraction with peak>0.01 | PASS |
| onset_latency_polarity_1 | test_ood_size | both | 1 | >=0.95 begin in [0.2,0.38] s | PASS |
| static_initial | train | both | 0 | <=0.01 peak | PASS |
| static_terminal | train | both | 0 | <=0.01 peak | PASS |
| translating_initial | train | both | 0 | <=0.01 peak | PASS |
| loom_response | train | LC4_like | 1 | >=0.95 fraction with peak>0.01 | PASS |
| loom_response | train | LPLC2_like | 1 | >=0.95 fraction with peak>0.01 | PASS |
| onset_latency | train | both | 1 | >=0.95 begin in [0.2,0.38] s | PASS |
| static_initial_polarity_-1 | train | both | 0 | <=0.01 peak | PASS |
| static_terminal_polarity_-1 | train | both | 0 | <=0.01 peak | PASS |
| translating_initial_polarity_-1 | train | both | 0 | <=0.01 peak | PASS |
| loom_response_polarity_-1 | train | LC4_like | 1 | >=0.95 fraction with peak>0.01 | PASS |
| loom_response_polarity_-1 | train | LPLC2_like | 1 | >=0.95 fraction with peak>0.01 | PASS |
| onset_latency_polarity_-1 | train | both | 1 | >=0.95 begin in [0.2,0.38] s | PASS |
| static_initial_polarity_1 | train | both | 0 | <=0.01 peak | PASS |
| static_terminal_polarity_1 | train | both | 0 | <=0.01 peak | PASS |
| translating_initial_polarity_1 | train | both | 0 | <=0.01 peak | PASS |
| loom_response_polarity_1 | train | LC4_like | 1 | >=0.95 fraction with peak>0.01 | PASS |
| loom_response_polarity_1 | train | LPLC2_like | 1 | >=0.95 fraction with peak>0.01 | PASS |
| onset_latency_polarity_1 | train | both | 1 | >=0.95 begin in [0.2,0.38] s | PASS |
| static_initial | validation | both | 0 | <=0.01 peak | PASS |
| static_terminal | validation | both | 0 | <=0.01 peak | PASS |
| translating_initial | validation | both | 0 | <=0.01 peak | PASS |
| loom_response | validation | LC4_like | 1 | >=0.95 fraction with peak>0.01 | PASS |
| loom_response | validation | LPLC2_like | 1 | >=0.95 fraction with peak>0.01 | PASS |
| onset_latency | validation | both | 1 | >=0.95 begin in [0.2,0.38] s | PASS |
| static_initial_polarity_-1 | validation | both | 0 | <=0.01 peak | PASS |
| static_terminal_polarity_-1 | validation | both | 0 | <=0.01 peak | PASS |
| translating_initial_polarity_-1 | validation | both | 0 | <=0.01 peak | PASS |
| loom_response_polarity_-1 | validation | LC4_like | 1 | >=0.95 fraction with peak>0.01 | PASS |
| loom_response_polarity_-1 | validation | LPLC2_like | 1 | >=0.95 fraction with peak>0.01 | PASS |
| onset_latency_polarity_-1 | validation | both | 1 | >=0.95 begin in [0.2,0.38] s | PASS |
| static_initial_polarity_1 | validation | both | 0 | <=0.01 peak | PASS |
| static_terminal_polarity_1 | validation | both | 0 | <=0.01 peak | PASS |
| translating_initial_polarity_1 | validation | both | 0 | <=0.01 peak | PASS |
| loom_response_polarity_1 | validation | LC4_like | 1 | >=0.95 fraction with peak>0.01 | PASS |
| loom_response_polarity_1 | validation | LPLC2_like | 1 | >=0.95 fraction with peak>0.01 | PASS |
| onset_latency_polarity_1 | validation | both | 1 | >=0.95 begin in [0.2,0.38] s | PASS |
| zero_contrast | fixtures | both | 0 | exactly 0 | PASS |
| matched_polarity | fixtures | both | 0 | exactly 0 | PASS |
| reproducibility | fixtures | both | 0 | exactly 0 | PASS |
| future_frame_causality | fixtures | both | 0 | exactly 0 | PASS |
| prefix_causality | fixtures | both | 0 | exactly 0 | PASS |
| metadata_argument_rejection | fixtures | both | 0 | exactly 0 | PASS |
| clipping_border | fixtures | both | 0 | exactly 0 | PASS |
| clipping_offscreen | fixtures | both | 0 | exactly 0 | PASS |
| clipping_fullfield | fixtures | both | 0 | exactly 0 | PASS |
| fractional_timestamps | fixtures | both | 0 | exactly 0 | PASS |
| causal_availability | fixtures | both | 0 | exactly 0 | PASS |
| seconds_ms_availability | fixtures | both | 0 | exactly 0 | PASS |
| dataset_integrity | fixtures | both | 0 | 0 collisions; 1024 records, 256 families | PASS |
| phase6_tests | fixtures | both | 0 | 0 failures/errors | PASS |

## Limitations / unresolved

Engineering proxy for a single circle on uniform background, not biological activity, radial-motion-opponency circuitry, receptive fields or spikes/s. Border-touching scenes suppress input rather than implement biological clipping compensation. Raw frame sets are never persisted by this validation; only hashes and encoded arrays are saved. Holding past the final timestamp requires an external episode end. All scientific hypotheses, biological calibration, synthetic fields/steering, complex scenes/flicker and Phase 7+ remain unresolved. The frozen NT confidence documentation mismatch is recorded in the specification, not repaired. A failed gate is a result, not permission to alter cutoffs or labels.
