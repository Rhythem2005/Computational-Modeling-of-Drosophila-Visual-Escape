# FLY behavioral-validation proposal v1 — 27 October 2026

**Status: planning only; implementation and execution not authorized.** Keep Phase 11 training paused. This proposal does not modify the frozen open-loop experiment, choose new seeds or thresholds, create new world fixtures, or authorize held-out evaluation. It proposes a separate behavioral comparison that can use existing trained models without completing 120 trials. No dependencies, commits or pushes are needed.

## 1. Current evidence and model availability

Read first: [behavior readiness review](../phase11/audits/behavior_readiness_20261027/README.md). The [Phase 9 protocol](../phase9/protocol.md), [configuration](../phase9/environment_config.yaml) and [saved validation report](../phase9/results/validation_report.md) define the world and existing endpoints. The [saved-score audit](../phase11/audits/saved_score_accuracy_20261026/README.md) verifies calibration consistency, not generalization.

Fresh read-only inspection using `./venv/bin/python -B` confirms:

| Item | Current saved state |
| --- | --- |
| Training/calibration completion | 45/120 trials; 272/816 calibration conditions |
| Selected GRU records | 22; selection records alone are insufficient |
| Selection plus completed calibration chains verified | 20: seeds 55100–55109 for uniform_population and for mapping 55010 |
| Selected but uncalibrated | Mapping 55011, seeds 55100 and 55101: excluded |
| Partial trial | train_55011_55102_0p001: epoch 51, offset 256, 816 Adam updates, finished=false; history ends at epoch 50 |
| Operational observation | No Phase 9/11 worker observed in process inventory; worker lease available at check; saved pause and exit 130/final-publication records agree |

The incomplete schedule has **20/60 selected-and-calibrated GRUs**. These are individual comparison models, not an implemented voting ensemble. Even though two mapping-specific sets have ten members each, the full six-mapping schedule remains incomplete. Never describe the partial trial as completed or calibrated, and never resume it to fill this proposal's roster.

[Inspection script](inspect_saved.py) and [machine-readable verification](saved_state_verification.json) record checkpoint payload/NPZ hashes, completed-report consistency, earliest-best epoch metadata, both-rate candidate ordering, selected weights, calibration payload/artifact hashes, provenance, execution sources and unchanged production pointers. Historical path relocation is read-only and recorded in the script. This is not numerical model replay or a replacement for full loader/source-contract validation at implementation. The existing source-compatibility guard was checked, not edited. No neural inference, simulation, training, test suite or held-out evaluation ran.

## 2. Endpoints: danger, avoidance and unnecessary escape

Retain the existing Phase 9 definitions without tuning the world or motor plant:

- **Danger:** evaluator-only analytic contact between an obstacle and the stationary initial fly during the inclusive [0,1000] ms horizon. Expansion alone is not danger. Geometry, labels and stationary contact time never enter a controller.
- **Dangerous escape success:** a first request strictly before stationary-fly contact, no obstacle or boundary contact through the inclusive horizon, and final clearance at least the existing 1 world unit. Report request success and actual physical avoidance separately. A timely request followed by collision is an avoidance failure.
- **Harmless false alarm:** any request during a harmless episode, including pre-onset requests and the expanding near-miss. Report requests, actual movement and movement cost separately. Harmless survival is not a successful escape.
- **Physical safety:** collision/boundary counts, failure time/object, minimum swept clearance, final clearance, survival to one second and termination versus horizon truncation. Contact at 1000 ms is failure; no decision at 1000 ms is allowed.
- **Timing and cost:** first request, pre-onset flag, onset-relative latency where defined, scheduled actuation, first motion, latched turn and path length. Retain Phase 9's `dangerous_miss` field as its request-timing metric; do not confuse it with all escape-success failures.

Publish exact counts and denominators for dangerous and harmless fixtures separately, per model and mapping. Do not combine these into balanced accuracy, a reward, or an apparently larger sample of independent threats. Repeated mappings, model seeds and exact reruns do not increase the number of world geometries. A pre-onset request remains visible even if it satisfies the historical escape-success definition; add an explicit no-pre-onset-request check for the proposed engineering target without changing that saved definition.

## 3. Fair comparison and explicit action semantics

The proposed primary comparison isolates **initiation timing with the existing neutral retreat command**. Every active controller emits a scalar first request and passes the existing turn `u=0` to the same actuator. No-action never requests. Reusing zero is an explicit proposed controller condition, not a change to Phase 9's existing spatial steering evidence. Do not invent GRU steering from its hidden state, sign of its scalar score, threat geometry or circuit DN outputs.

| Controller | Observation/score and decision | Motor command |
| --- | --- | --- |
| Anatomical circuit | Frozen encoder, Circuit v2 native dynamics, frozen matching circuit threshold and closed 20 ms initiation rule | First event requests neutral retreat |
| Simple trigger | Existing `feature_only` scaled population-channel mean; own verified matching calibration, same persistence/latch | Same neutral retreat |
| No-action | Same initial scenario and renderer; controller requests disabled | No movement |
| Each eligible GRU | Same ordered 321-element per-neuron drive; float64 16-unit GRU; sigmoid scalar score; own selected calibration | Same neutral retreat |

Use native circuit dynamics only in this bounded proposal. Neither gain selection nor extra controls are needed to test whether escape is useful versus no action and whether a simple visual trigger suffices. The simple rule is already implemented in Phase 10; no newly fitted heuristic or oracle trigger is proposed. Verify its and the circuit's matching calibration freezes before inclusion. The existing linear control and structural nulls remain available for a later separately specified architecture question; this comparison cannot establish anatomical superiority.

All controllers share camera, encoding/body-ID order, input scale 0.4 applied once, observation availability and world/actuator parameters. At identical physical histories, their observation bytes and input vectors must match. After different actions, each receives its own action-dependent observations; forcing identical full trajectories would remove feedback. A common saved input trace may test adapter equivalence, but cannot substitute for closed-loop outcomes.

Keep the 20 ms delay, speed cap 20, acceleration cap 400, 1 ms world segments, bounds, radii, motion onset and one-second horizon exactly as configured. Preserve the initial zero speed and ensuing one-segment delay to first displacement. No adaptive steering, yaw, longer horizon, noise injection or biomechanics is included. Existing Phase 9 DN-steered runs across all five synthetic mappings remain labeled historical engineering demonstrations; they are not pooled into the neutral-action comparison.

## 4. Causal adapter and resets

Implement later in a separate namespace with its own protocol/manifest and output writer; do not edit frozen Phase 9/10/11 code or bypass source guards. Phase 9's `ClosedLoopRunner` hardcodes circuit/decoder dependencies, and `activity_io.save_episode` restricts output to Phase 9 and assumes neural/DN arrays. Reuse verified world primitives through an approved execution snapshot; provide a new controller interface and schema rather than pretending GRU hidden units are neurons or DN activity.

At each integer k before termination: expose only frames with exact timestamps n/60 <= k/1000; causally encode the available prefix; read the current controller state and score; apply the frozen persistence/first-event rule; latch any first motor request; advance the physical segment and controller state using the current held input. Fractional-timestamp images are rendered at their physical positions and become available only at the next eligible integer update. Never use an epsilon to admit a future frame.

**GRU timing is critical:** Phase 10 `GRU.forward` returns the score of h[k] before applying input[k]. The streaming adapter must emit sigmoid(h[k]·w+b), then update with 0.4×drive[k] using the exact reset-before gates and update convention. Do not shift scores one tick earlier, perform BPTT, fit weights, change arithmetic/dtype, or process only at camera frequency. Its initial score can be nonzero because of learned output bias; retain that and any early alarm.

Reset each episode's circuit/filter/GRU state, encoder prefix/history, held input, frame counter, decoder persistence history and latch, actuator request/direction/speed, world and diagnostics. No warmup, hidden carryover between fixtures or ensemble state. The feature-only score uses the current causal held drive as in its existing batch definition; its timing need not imitate the circuit's state lag. Preserve closed 20 ms persistence, first event only and half-open [0,1000) decisions, including early events. On fractional collision stop exactly: no decision after contact and no fictitious completed-step state. Later threshold crossings cannot change direction or restart delay.

## 5. Model inclusion and failure rules

Freeze an outcome-independent roster from the saved-state cutoff before any new behavior run. For every included seed require both completed rate candidates, checkpoint/report/parameter integrity, earliest best validation checkpoint, then minimum validation BCE across rates with smaller-rate tie break, the selected proof and completed matching calibration freeze. Preserve the frozen objective, optimizer, batch size 16, initialization/shuffle conventions, partitions and original ten seeds. No behavior score may select a checkpoint, learning rate, model, mapping or threshold.

Include all ten qualifying seeds in each included mapping, including always-silent collapsed models. Keep their original thresholds, candidate ranking, persistence and calibration provenance; no threshold averaging, best-seed reporting, replacement seed or behavioral rescue fitting. A silent GRU is a valid included model whose dangerous misses count, not a missing model. All results must be listed per seed; descriptive across-seed summaries cannot imply a new ensemble controller.

For corruption, source mismatch, missing calibration, nonfinite outputs or adapter failures: preserve evidence and distinguish model failure from infrastructure failure. Do not omit a difficult scenario from a denominator or count a crash as successful avoidance. Report unresolved runs and conservative success bounds with unresolved runs treated as unsuccessful, alongside verified physical failures; never fabricate collision times for crashes. Abort the affected comparison on integrity/causality defects. A corrected infrastructure rerun uses the same identity and retained attempt history, requires review of the defect, and consumes the fixed budget; no automatic redraw or extra run. If a required roster member cannot be verified, report that set incomplete rather than replacing it.

## 6. Calibration and independent evaluation boundaries

**Proposed first stage: engineering fixtures only, with zero new fitting.** Reuse verified open-loop decoders and clearly label world-domain transfer as uncalibrated. The eight successful primary GRUs, two silent GRUs and perfect circuit/control validation scores came from reused selection/calibration validation data. They are not independent results. The smallest-positive-float thresholds (5e-324 for the audited non-GRU primary conditions) retain their exact values and silence-boundary interpretation. Do not infer noise tolerance.

The known Phase 9 static and near-miss cases, all five fixture geometries and all prior observations are development evidence, never a behavioral holdout. Existing open-loop benchmark test/OOD cohorts remain untouched and do not become world evaluation data by renaming them.

**Independent behavioral evaluation is a separate, currently blocked protocol stage with a zero execution budget in this proposal.** Before authorizing it, document the target world-condition population, exact condition manifest/generation rules and any authorized seeds, geometry-family grouping, disjoint calibration/evaluation membership, sampling unit, sample size/precision justification, endpoint-specific acceptance targets, multiplicity policy and compute cap. Keep matched variants and related geometry families together. Do not invent those values here or claim that partitioning the five already inspected fixtures creates independence.

If new world calibration is desired, authorize it separately, specify the calibration-only objective/candidate rule before outcomes, fit only there and freeze every model/decoder before opening independent conditions. It creates separately versioned decoders and cannot overwrite open-loop freezes or be reported as the present unchanged-threshold transfer. The original validation FPR constraint <=0.05 is not automatically a behavioral acceptance threshold. Any changes after independent evaluation invalidate confirmation on those same cases; preserve them as exploratory and require a separately authorized evaluation design.

## 7. Bounded proposed run manifest and resource budget

These are proposed future runs requiring approval of this document and adapter review. No new scenario bytes are defined. Resolve fixture identities from existing Phase 9 configs, bind hashes and declare the new controller/neutral-action condition before execution.

| Block | Existing fixtures | Controllers | Unique episodes | One exact repeat each | Total cap |
| --- | --- | --- | --- | --- | --- |
| Primary uniform | Head-on, left, right, static, near-miss | Circuit + feature-only + no-action + all 10 primary GRUs = 13 | 65 | 65 | 130 |
| Secondary mapping 55010, descriptive only | Existing left and right fixtures | Circuit + feature-only + no-action + all 10 matching GRUs = 13 | 26 | 26 | 52 |
| Total | No new geometries | Separate per-model outcomes | 91 | 91 | **182** |

Mapping 55010 is included because it is the only secondary mapping with all ten selected-and-calibrated models at the saved cutoff, not because of performance. Report its missing harmless coverage prominently; it cannot answer secondary harmless false-alarm performance. Mappings 55011–55014 remain absent from this new comparison, with explicit coverage gaps. Do not add static/near-miss secondary combinations without documenting and authorizing those new conditions. No-action duplicates across mapping blocks are paired bookkeeping, not new physical evidence.

Each episode lasts at most one simulated second: at most 182,000 decision ticks and 10,920 camera frames under the existing half-open camera schedule. Exact repeats are reproducibility checks, not independent observations. Count aborted attempts against the episode cap. Never exceed the cap to finish a favorable subset.

Proposed operational ceilings on the M4/16 GB machine: one CPU worker, 4 GiB process RSS, 2 GiB new artifact output, 30 minutes for targeted engineering checks and 60 minutes for behavioral episodes/reporting. These are stop budgets, **not measured runtime estimates or promises**. Measure the first scheduled circuit/control/GRU episodes within the cap, record elapsed time/RSS/disk, and stop with partial coverage if projected completion exceeds the ceilings; do not change models, timestep, storage precision or fixtures to fit. No training or full 120-trial continuation, new data caches, dependency installs or benchmark evaluation is included. Preserve other-worker, memory, thermal and low-battery gates; AC remains optional with verified battery >=20% at startup. Disk estimation stays advisory; the new artifact-output cap is a separate proposal limit. Do not edit orchestration to introduce these checks during planning.

## 8. Required adapter review and meaningful tests before runs

1. **Artifact loading and roster:** reject wrong model/mapping/body order, dtype/shapes, hash/source mismatch, partial trial or uncalibrated selection. Exercise exact operational source certificates in the approved snapshot, record actual fingerprints, and verify parent preservation. No loader may invoke training or evaluate held-out clips.
2. **Streaming equivalence:** circuit wrapper versus existing Phase 9 behavior; feature score versus existing batch function; GRU prefix logits, hidden states, sigmoid scores, sustained scores and first event versus the unchanged `GRU.forward`/decoder on approved development traces. Preserve operation order for exact equality; any floating-point discrepancy requires diagnosis and review, not a conveniently loose tolerance. Include learned bias at t=0 and score-before-update alignment.
3. **Causality and resets:** perturb only future development frames and require equal past outputs; check 16.666… ms availability at 17 ms, input scaling once, episode order independence, first-event latch, silent thresholds, early requests and no decision at 1000 ms. Synthetic unit inputs are test fixtures only, not new behavioral conditions or fitted examples.
4. **World/action contract:** neutral command identical across active models, no-action truly stationary, common pre-action images, changed future images after movement, exact delay/acceleration/first-displacement schedule, fractional and horizon contact precedence, no post-terminal state/decision. Reuse existing geometry cases where possible; do not regenerate frozen outputs.
5. **Metrics and storage:** independently recompute request/latency, swept clearance, success/false alarm and path length from saved trajectories; verify schema roundtrip and hashes, controller-state distinctions, failure retention and deterministic repeats. Use a new output directory, never Phase 9's protected writer or canonical Phase 11 results.

Run only relevant adapter/integration checks later under the check budget; do not automatically rerun the entire historical suite. A failed necessary check blocks behavior execution. Test counts quoted from existing reports remain historical until a new authorized run produces its own logs.

## 9. Sensory validity and acceptance gates

Save per-frame validity and denominator, clipping/capping, unsupported silhouettes/edge clipping, near-plane/behind-camera counts and timing relative to request/movement. Report full-episode and pre-request validity (whole available episode if no request), first invalid time, finite-state checks and direct-DN input checks. Include validity for no-action paths too. Movement changes validity, so filtering whole trajectories afterward can bias comparisons.

Retain every scheduled episode in the main outcome table. Annotate failures and unsupported-input exposure; present any fully valid subset only as a secondary description with exact selection rule and coverage. Never count disappearance or invalid encoding as safety or silently repair the encoder. A whole-episode in-domain claim requires all relevant frames valid; otherwise the outcome is an engineering result with domain limitations. Existing saved valid fractions of 71.7–100% already prevent a blanket in-domain claim.

Acceptance is tiered:

- **Implementation gate:** every required causal, reset, artifact, metric and preservation check passes; no unresolved integrity defect. Exact reruns match saved numerical outcomes under the recorded environment. This establishes engineering correctness, not reliable escape.
- **Fixture target for each active controller:** all three primary dangerous geometries meet the existing success criterion, both primary harmless fixtures have no request, and no pre-onset request occurs. Report component failures per seed rather than choosing a passing model. No-action must remain stationary and agree with analytic stationary contact/harmless geometry. The secondary block can assess only its two dangerous cases. This proposed all-fixture target is not a new decoder threshold or a population-rate estimate.
- **Current readiness:** the historical circuit passes dangerous demonstrations but fails this combined target because the near-miss triggers. Do not retune to hide that. Failure means the requested unnecessary-escape behavior remains unresolved, even if adapters pass.
- **Generalization gate:** unavailable until the independent protocol's population, sampling and quantitative risk/precision criteria are separately authorized and met. No confidence interval from three known threats/two harmless fixtures can certify representative reliability. A comparative benefit requires matched scenario outcomes with uncertainty over independent world families; if controls tie or evidence is insufficient, report that.

Engineering demonstrations establish that signals can move an abstract simulated fly and affect future images. Independent behavioral evaluation could support finite-horizon performance within a declared simulated domain. Neither establishes biological flight, learned motor control, permanent safety, realistic sensory robustness or anatomical wiring superiority. Training the conventional GRU does not alter anatomical weights or train the movement plant.

## 10. Reviewable next action

Approve or revise this bounded engineering proposal before implementation. That approval would cover a separately versioned adapter/protocol, required checks and at most the 182 specified episodes under the resource caps; it would not cover new conditions, world calibration, independent evaluation or training continuation. Freeze the exact roster/fixture hashes, action semantics, acceptance checks and execution provenance before the first run. Save outputs and any failures in a new behavioral study directory, preserving all prior source, configuration, checkpoint and evidence bytes.
