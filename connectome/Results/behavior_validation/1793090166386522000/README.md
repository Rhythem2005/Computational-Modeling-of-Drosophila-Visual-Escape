# Behavioral engineering comparison v1

Adapters and numerical/causal checks passed. Completed 91 unique fixture/controller combinations and 91 exact repeats.
These are five known geometries, not 182 independent threats. Frozen open-loop thresholds were reused without world calibration.

| Mapping / model | Danger success | Harmless requests | Physical failures | Fully valid episodes | Combined primary target |
| --- | --- | --- | --- | --- | --- |
| uniform_population/circuit | 3/3 | 1/2 | 0 | 5/5 | FAIL |
| uniform_population/feature_only | 3/3 | 1/2 | 0 | 5/5 | FAIL |
| uniform_population/no_action | 0/3 | 0/2 | 3 | 1/5 | not applicable |
| uniform_population/gru_55100 | 3/3 | 1/2 | 0 | 5/5 | FAIL |
| uniform_population/gru_55101 | 3/3 | 1/2 | 0 | 5/5 | FAIL |
| uniform_population/gru_55102 | 3/3 | 1/2 | 0 | 5/5 | FAIL |
| uniform_population/gru_55103 | 3/3 | 1/2 | 0 | 5/5 | FAIL |
| uniform_population/gru_55104 | 3/3 | 1/2 | 0 | 5/5 | FAIL |
| uniform_population/gru_55105 | 3/3 | 1/2 | 0 | 5/5 | FAIL |
| uniform_population/gru_55106 | 0/3 | 0/2 | 3 | 1/5 | FAIL |
| uniform_population/gru_55107 | 3/3 | 1/2 | 0 | 5/5 | FAIL |
| uniform_population/gru_55108 | 0/3 | 0/2 | 3 | 1/5 | FAIL |
| uniform_population/gru_55109 | 3/3 | 1/2 | 0 | 5/5 | FAIL |
| 55010/circuit | 2/2 | 0/0 | 0 | 2/2 | not applicable |
| 55010/feature_only | 2/2 | 0/0 | 0 | 2/2 | not applicable |
| 55010/no_action | 0/2 | 0/0 | 2 | 0/2 | not applicable |
| 55010/gru_55100 | 2/2 | 0/0 | 0 | 2/2 | not applicable |
| 55010/gru_55101 | 2/2 | 0/0 | 0 | 2/2 | not applicable |
| 55010/gru_55102 | 2/2 | 0/0 | 0 | 2/2 | not applicable |
| 55010/gru_55103 | 2/2 | 0/0 | 0 | 2/2 | not applicable |
| 55010/gru_55104 | 2/2 | 0/0 | 0 | 2/2 | not applicable |
| 55010/gru_55105 | 2/2 | 0/0 | 0 | 2/2 | not applicable |
| 55010/gru_55106 | 2/2 | 0/0 | 0 | 2/2 | not applicable |
| 55010/gru_55107 | 2/2 | 0/0 | 0 | 2/2 | not applicable |
| 55010/gru_55108 | 2/2 | 0/0 | 0 | 2/2 | not applicable |
| 55010/gru_55109 | 2/2 | 0/0 | 0 | 2/2 | not applicable |

The full GRU schedule remains incomplete: 20/60 selected-and-calibrated models were used; two selected but uncalibrated models and the partial trial remain excluded.
Secondary mapping 55010 has only left/right dangerous fixtures and no harmless coverage. No favorable seed or threshold was selected.
Per-episode onset/request/motion timing, swept/final clearance, collisions, movement cost, sensory validity and input-domain limitations are in summary.json and episode records.
The engineering gate establishes implementation consistency. Combined behavioral failures remain failures; no tuning or new conditions were introduced to rescue them.
No training, calibration, held-out evaluation, dependency installation, commit or push occurred. Biological flight, permanent safety and anatomical superiority remain unestablished.
