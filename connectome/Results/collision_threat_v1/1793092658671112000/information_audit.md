# Stage A — saved-image information and timing audit

Processed 91 unique saved trajectories. No model inference, classifier fitting, threshold search, world simulation, training or held-out evaluation occurred.
The five uniform no-action paths provide the primary information diagnostic. Their dangerous trajectories end at collision; no post-contact frames were fabricated.

| Known case | First usable motion measurement ms | First nonzero bearing motion ms | First positive extent growth ms | Legacy circuit request ms | Stationary contact ms |
| --- | --- | --- | --- | --- | --- |
| world_head_on | 17 | None | 217 | 239.0 | 920.0 |
| world_left | 17 | None | 217 | 239.0 | 923.3738971823078 |
| world_right | 17 | None | 217 | 239.0 | 923.3738971823078 |
| world_static | 17 | None | None | None | None |
| world_near_miss | 17 | 217 | 217 | 239.0 | None |

Head-on and near-miss images first differ at an available tick of 217 ms; their original size/growth channels first differ at 217 ms. They are not exactly identical observations.

Stage A review: **PROCEED_TO_EXACT_RULE_SPECIFICATION**. Image motion is available before the legacy request: True.
This supports constructing a candidate rule, not an information-theoretic proof, a fitted classifier result, or a demonstrated safe later request time.
The primary encoder does not explicitly retain centroid/bearing motion. More training on its original task is not established as a remedy.

Missing image evidence remains unknown. Empty masks cannot distinguish absence, near-plane disappearance, or an object behind the camera. Renderer depth diagnostics are saved audit references only and do not enter the extractor.
All episodes remain included. Unsupported-image exposure is reported in validity_report.json; it is not used for outcome-dependent exclusions.

Stage B remains disabled until the exact candidate equations, assumptions, persistence and finite calibration manifest receive the reserved review/authorization. No prototype episode budget has been used.
The original 45 completed trials and partial checkpoint remain preserved. The earlier five fixtures remain development evidence; no generalization or biological claim is made.
