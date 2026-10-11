# FLY research protocol v1.0

## Question and scope

Does the detailed connectivity of the selected MaleCNS circuit contribute useful looming responses beyond matched randomized connectivity, population-level structure, and simple feature-based models, under explicit encoding and dynamical assumptions?

The frozen circuit remains the 321-neuron, 11,557-edge, 91,023-synapse Circuit v2. Numerical correctness of Phase 4 and correct stimulus generation in Phase 5 are engineering evidence, not evidence of behavioral validity. This protocol preserves their artifacts and behavior.

Primary task: **open-loop synthetic looming discrimination and response timing**. A positive episode contains radial expansion; negatives contain matched stationary or translating objects. Labels do not assert a physical collision, predator or biological escape. Directional takeoff and closed-loop avoidance require separate later protocols.

## Hypotheses and interpretation

| ID | Predeclared assessment | Supporting evidence / failure meaning |
| --- | --- | --- |
| H1: useful response | Circuit balanced accuracy exceeds chance on `test_id`. | 95% family-bootstrap interval lower bound >0.5. Practical goal additionally requires timely TPR >=0.80 and negative FPR <=0.10. These cutoffs are engineering choices. Failure can implicate encoding, dynamics or decision assumptions; it does not disprove fly escape. |
| H2: detailed wiring | Circuit improves over both the population-averaged control and the mean of 30 weight-shuffle networks on `test_id`. | Each balanced-accuracy difference >=0.03 and each 97.5% paired bootstrap interval lower bound >0. The two intervals implement Bonferroni coverage for the two primary comparisons. If this fails, do not claim an advantage of detailed wiring. |
| H3: robustness | Describe performance on three separately held-out parameter axes and under modeling perturbations. | Report each cohort and ID-to-mean-OOD drop; <=0.10 is a practical goal, not a new significance test. An advantage only under selected mappings or tuning is conditional. No universal robustness claim. |

H1 is a prerequisite for a useful-system claim. H2 is a prerequisite for the specified detailed-wiring claim. NN performance and secondary controls are descriptive comparisons, not replacements selected after seeing test results. A null result is informative: a simpler circuit may explain the selected computation under these assumptions. No scientific outcome exists yet.

## Inputs and representations

Primary encoder supplies two causal global signals, one LC4-like and one LPLC2-like, broadcast uniformly within each visual population. This deliberately avoids assuming individual receptive fields. Uniform input can still test effects of heterogeneous wiring and recurrent dynamics, but cannot recover object location or establish a spatial mechanism. Left/right and population size differences must be reported, not automatically interpreted as steering.

LC4-like expansion-speed and LPLC2-like expansion-selective size features are engineered hypotheses informed by literature, not measured activity. LPLC2-like activity must be tested against size-matched static objects and translation; raw object area is not sufficient evidence of looming selectivity. Exact encoder equations, normalization and temporal filters must be frozen during Phase 6 before network comparisons. A failure of standalone encoding gates is reported before tuning the circuit.

The encoder receives only frame arrays and relative timestamps. No stimulus ID/type, label, initial position, radius, speed, expansion parameters, future frame, test normalization statistic or action target may enter it. Generator metadata may be used by evaluators to check geometry. An oracle-feature run is a separately labeled diagnostic, excluded from primary comparisons.

Secondary spatial inputs use synthetic receptive fields assigned independently of outgoing DN weights and outcomes, with the five mapping seeds in YAML. Preserve type/side membership when permuting field-to-neuron assignments. All compared architectures receive exactly the same per-neuron encoded inputs for a mapping. Hemisphere and image-plane conventions remain modeling assumptions. Steering remains gated on a defensible mapping; soma coordinates or fitted DN preferences are not retinotopy.

## Dataset and held-out design

Each independently sampled family has four clips: looming, static at the initial radius, static at the final sampled looming radius, and translation at the initial radius. They share contrast, center, resolution and timing. Every family stays in one cohort/split. Continuous geometry and a content fingerprint prevent duplicate configs across partitions; ID and provenance seed are excluded from that fingerprint. This check is not a proof that rasterized frames can never coincide; future dataset ingestion must also check actual frame hashes and group any collisions.

All clips are 256x256 uint8, 60 fps, 1 s, with motion onset 0.2 s. Centers are sampled within [64,192] px per axis. Both contrast polarities are included, without assuming equal biological sensitivity. A pinhole looming trajectory uses `Z0=50`, `f_R=r0*Z0`, and `v=q*Z0/0.8`, where q is fractional distance reduction over the active interval. Require Z>1 throughout duration. Final static size matches the last sampled frame, not the unsampled endpoint. No angular calibration is inferred.

| Cohort | Families / episodes | Initial radius (px) | q range | Absolute contrast |
| --- | --- | --- | --- | --- |
| train | 64 / 256 | 8–16 | 0.25–0.55 | 48–96 |
| validation | 32 / 128 | 8–16 | 0.25–0.55 | 48–96 |
| test_id | 64 / 256 | 8–16 | 0.25–0.55 | 48–96 |
| test_ood_size | 32 / 128 | 18–24 | 0.25–0.55 | 48–96 |
| test_ood_growth | 32 / 128 | 8–16 | 0.65–0.75 | 48–96 |
| test_ood_contrast | 32 / 128 | 8–16 | 0.25–0.55 | 12–32 |

These are modest initial sample counts, not a power-analysis guarantee. Low-contrast, fast-growth and size cohorts vary different latent parameters; derived radius/speed may co-vary. Claims of isolated causal feature effects require additional orthogonal stimulus sweeps. Clipping, flicker and contraction are later stress tests requiring new documented fixtures; none are implemented by this protocol.

## Decision rule and endpoints

Primary connectome score is mean bilateral DNp01 activity; secondary DNs are exploratory readouts. Record all traces before decoding. Use the Phase 4 defaults of gain 0.5, tau 10 ms, input_scale 0.4 and Euler dt 1 ms as the primary dynamics. Never tune these defaults separately for the original network after inspecting test performance.

A decision occurs after the score is at or above its selected threshold continuously for 20 ms. Every model shares this duration rule. Primary observation window is [0.2,1.0) s. Report the complete episode, including pre-onset alarms; an earlier decision cannot be reset to create a valid later response. Positive timely TPR counts first decisions within the window; negative FPR counts any decision during the full episode. Define primary balanced accuracy as (timely TPR + 1 - negative FPR)/2. This event-based definition intentionally penalizes premature positives; it differs from ordinary clip classification and must be labeled explicitly.

Secondary metrics: pre-onset alarm rate, response probability by control subtype, median onset-relative latency among timely detections, and latency with misses assigned the 0.8 s horizon for an all-positive summary. Always report misses alongside detected-only latency. A final-time decision outside the sampled interval is not a detection. Do not infer sub-frame sensory precision from a 1 ms numerical integration step: input arrives only at the 60 Hz sample times.

Resampling is causal zero-order hold: a frame-derived signal becomes available no earlier than that frame timestamp, and is held until the next frame. No interpolation with future frames. Initial state and warmup protocol are identical across circuit controls.

## Controls and permitted fitting

| Model | Purpose / construction |
| --- | --- |
| Frozen Circuit v2 | Reference architecture; measured unsigned counts, assumed positive signs and unchanged primary dynamics. |
| Feature-only decision | Uses the same encoded information with a small predeclared combination rule; tests whether the encoder suffices. |
| Linear temporal model | Causal leaky features with tau=10 ms and a trained linear readout of the same per-neuron input; tests generic filtering. Fit on train only, with documented parameter count. |
| Population-averaged matrix | Retains 321 nodes and total normalized weight per directed type×side block; distribute equally across eligible pairs, excluding diagonal edges. It deliberately removes individual degree heterogeneity. Uses the same simulator. |
| Weight shuffle (primary null) | Permute nonzero weights among existing edges within directed type×side blocks; retain topology, degrees, block totals, node identities and the weight multiset per block. 30 predefined seeds derived from the design seed. This tests weight placement, not topology. |
| Degree-preserving rewiring (secondary) | Directed double-edge swaps within type×side blocks, no new self-loops/duplicate edges. Preserve node in/out degree and each block weight multiset; strengths per neuron need not be preserved. Report achieved swaps and mixing diagnostics; failed mixing does not count as a valid shuffled control. |
| Conventional NN (reference) | One causal GRU with 16 hidden units and a scalar readout, consuming the same input vectors. Adam learning rates 0.0003/0.001, 10 specified seeds, <=200 epochs and patience 20. Train parameters only on train; validation selects rate and stopping checkpoint. |

Frozen circuit controls fit only an episode threshold. Up to 31 thresholds are derived from training negative sustained-score quantiles, plus an always-silent sentinel (32 candidates total). Use quantile levels equally spaced from 0 to 1. The sustained score at time t is the minimum over the preceding 20 ms; episodes use its maximum. At the beginning of a run, no decision is eligible before 20 ms has elapsed. Validation selects highest timely TPR among candidates with full-episode FPR<=0.05; ties prefer smaller FPR then higher threshold. The silent sentinel makes the constraint feasible. Freeze this selection before test use; calibrate every null network using the same rule and its own training/validation responses.

Feature-only and linear readout parameters must use training labels only. GRU training uses episode-level binary cross entropy on maximum causal score over the observation window; the same threshold/persistence rule is applied for evaluation. Report pre-onset responses separately. Trainable baselines are performance references with larger fitting opportunities; they cannot by themselves identify a wiring effect. A future equally task-optimized connectome comparison requires a separate protocol amendment.

Report stability, input/output scale, clipped fraction, runtime and trainable parameters for every architecture. Native-gain runs keep gain=0.5. Instability/nonfinite outputs are failed runs, not silently redrawn null networks; report valid counts. H2 cannot be confirmed from the primary condition if any required network fails: excluding failures or penalizing failed controls could manufacture a wiring advantage. For operational utility only, provide a separately labeled worst-case sensitivity assigning failed runs balanced accuracy 0 and FPR 1.0 (imputed, not measured); never use it to confirm H2. Exceeding 1% clipped neuron-time samples invalidates a linear-regime interpretation, but results remain visible.

A secondary stability-matched comparison rescales each recurrent matrix by a single non-learned gain to spectral radius 0.6958315414466647, the saved Phase 4 reference value. Require continuous/discrete stability checks as well; zero spectral radius uses the fixed gain and is reported separately. This control distinguishes topology from amplification. It is a separate condition, not a replacement chosen when primary results are unfavorable.

## Statistical and reproducibility rules

Use families, not individual frames or four correlated clips, as resampling units. For circuit versus population-average, pair families. For circuit versus shuffled ensemble, resample families and shuffle seeds independently, retain paired scenario evaluations, and average across null networks. Use 2,000 bootstrap resamples and the fixed bootstrap seed. Confidence intervals express variation over sampled scenarios and modeled randomizations, not biological flies or populations. Show effect sizes, distributions and failure counts as well as intervals.

H2 uses two predeclared comparisons with 97.5% percentile intervals. Other metrics/cohorts/ablations are exploratory unless separately amended before evaluation. Shared deterministic reruns are reproducibility checks, not additional independent observations. No selecting the best mapping, decoder or shuffle from test results.

For every run save design/manifest/model/config hashes, encoder version, mapping/null/training seeds, thresholds, held-out predictions, traces, eligibility/failure flags, timing rule, environment versions and exact command. Make test plots only after model/threshold freeze. Protocol edits require a rationale and new version/lock; post-test changes are exploratory and need fresh independent evaluation for confirmatory claims.

## Later-phase gates

Phase 6: frame-only causal encoder passes standalone controls and records its assumptions. Phase 7: schema 1.0, body IDs, seconds-to-ms conversion, frame availability and state/readout timing are verified; simple controls run before decoder tuning. Phase 8: predefined initiation decoder; directional actions remain conditional on spatial evidence. Phase 9: world geometry, action constraints and collision definitions must precede closed-loop tuning. Actions must change later visual inputs to claim closed-loop avoidance. Phases 10–12 execute these controls and report all outcomes. An independently versioned circuit extension may study omitted pathways; it must not overwrite Circuit v2 or be selected to rescue this experiment.
