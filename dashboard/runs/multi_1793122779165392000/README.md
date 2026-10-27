# Approved multi-object development run

20 reservations; 18 audited recordings; 2 startup failures retained without retry.

| Controller | Dangerous escapes | Harmless requests | Completed |
|---|---|---|---|
| simple_trigger | 3/3 | 1/1 | 4 |
| frozen_latched | 2/2 | 1/1 | 3 |
| planner_only | 3/3 | 0/1 | 4 |
| circuit_planner | 3/3 | 0/1 | 4 |
| no_action | 0/2 | 0/1 | 3 |

The horizontal no-action reservation failed before computation because the old temporary snapshot had been removed. The vertical frozen-latched reservation failed before computation because ended viewer connections filled telemetry capacity. The verified historical snapshot was reconstructed byte-for-byte and the viewer cleanup was repaired. Neither failed reservation was retried. All 20 approved slots are now consumed.

Planner-only and circuit-armed planner have exactly matching physical trajectories, images and initiation events in all four scenes. These outcomes establish no anatomical contribution to avoidance. Multi-object images remain outside the frozen encoder’s validated domain; retain the sensory-validity and unknown-state fields in every report. One second and four hand-specified development scenes cannot establish continuous long-horizon navigation or generalization.

Existing scientific source/checkpoint preservation checks passed; training and held-out evaluation did not run. UI layout and speed parameters were unchanged. See analysis.json and each attempt’s verified.json for the full results.
