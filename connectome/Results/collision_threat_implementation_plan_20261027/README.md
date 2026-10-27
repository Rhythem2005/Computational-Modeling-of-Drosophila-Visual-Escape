# Collision-threat implementation plan v1 — 27 October 2026

**Planning only.** The requested deliverable is this implementation plan. No new controller, feature extractor, calibration, simulation, training or evaluation is implemented or run by it. Keep the 120-trial schedule paused. Future implementation must use a new protocol and namespace; the completed open-loop study components and behavioral engineering run remain unchanged.

The recommended next deliverable is a causal image-feature diagnostic and a small, interpretable collision-threat prototype. Finishing the original GRU schedule is a separate research objective, not a demonstrated remedy for the observed behavior.

## 1. What the results establish and what remains uncertain

Evidence: [completed behavioral comparison](../behavior_validation/1793090166386522000/README.md), [full per-model results](../behavior_validation/1793090166386522000/summary.json), [saved-file audit](../behavior_validation/1793090166386522000/saved_file_audit.json), and [implementation/provenance record](../behavior_validation/README.md).

| Finding | Consequence for implementation |
| --- | --- |
| Circuit and feature-only control each succeeded on three primary dangers, stayed silent on static, and escaped on harmless near-miss | Treat unnecessary escape as an unresolved endpoint. Existing integration is functional; the near-miss is not a plumbing failure. |
| Eight primary GRUs had that same outcome pattern; two silent GRUs collided on all three dangers | More of the same expansion-discrimination training is not established as a fix. Preserve silent models as failures; do not select favorable seeds. |
| All ten mapping-55010 GRUs succeeded on two dangers, with no harmless secondary coverage | This cannot establish mapping superiority or reduced false alarms. |
| Thirty adapter checks passed; 91 combinations and 91 repeats matched; protected files remained unchanged | Reuse the verified scheduling, loading, recording and actuator contracts. Do not loosen exact numerical checks or rebuild the plant to rescue results. |
| Five known geometries underlie the runs | All present cases are development evidence. Repeats and model seeds do not supply independent world generalization. |
| The primary encoder broadcasts two size/growth-derived channels; it does not explicitly pass image position or its motion | Missing threat-relevant information is a plausible bottleneck, not a proven impossibility result. Diagnose what the images and existing inputs contain before changing a model. |

The original objective distinguishes expansion from static/translation. A growing object can pass harmlessly. Optimizing that objective further need not improve collision avoidance. The anatomical weights and prescribed motor plant are not trained by Phase 11.

Fresh saved-state reading still gives 45/120 completed training trials and 272/816 completed calibrations. The unfinished `train_55011_55102_0p001` pointer remains epoch 51, offset 256, Adam updates 816, finished=false. Twenty selected/calibrated GRUs remain usable references; the two selected-but-uncalibrated mapping-55011 models remain excluded. These are point-in-time saved-file observations, not a fresh live process-status assertion.

## 2. Scope and causal boundaries

Initially retain the exact existing Phase 9 world, renderer, neutral command u=0, 20 ms actuation delay, acceleration cap 400, speed cap 20, 1 ms physical/controller grid, 60 Hz observations and inclusive one-second collision horizon. No steering adaptation, yaw, new motor parameters, longer horizon, stochastic disturbance or dependency installation is part of this proposal's prototype.

The new threat module may see only available images, their timestamps, approved camera constants, and its own causal state. Ground-truth object position/velocity/radius, future images, danger labels, contact times, fixture names, model success labels and scheduled motion onset are evaluator-only. A controller must discover motion from observations rather than use the known 200 ms onset. Do not infer physical clearance from image coordinates without a separately declared scale/shape assumption.

At millisecond k expose frames at n/60 <= k/1000, using the existing strict availability rule. Derivatives use actual camera timestamps and past samples, not 1 ms differences of repeated held frames. Reset all image history, derivative state, validity flags, model state and latches at each episode. Preserve the frozen legacy controller's score-before-update timing, scale 0.4 once, closed 20 ms persistence and original first-event latch. A new module gets its own explicit versioned decision semantics; it cannot silently change the old decoder.

## 3. Stage A — diagnose information and warning time from saved evidence

This is the first implementation slice to authorize. Use the completed run's existing NPZ/JSON files; do not rerun its 182 episodes. Hash-check the exact manifest and source episodes. Process at most the 91 unique saved trajectories; repeats are integrity checks only. Use the five uniform no-action paths as the primary threat-information diagnostic because their images do not already contain escape-induced motion. The no-action dangerous paths end at collision; never pad or infer post-contact observations.

Produce the following, without fitting a classifier or scanning decision thresholds:

1. **Information audit.** At each available frame, align the original channels, neural/GRU scores, validity, first request and first motion. Check exact equality or differences between dangerous and harmless prefixes; do not describe similar traces as identical. Record whether useful changes precede or follow the existing requests.
2. **New diagnostic image measurements.** Propose a separate extractor for foreground area/radius, centroid coordinates, normalized image bearing, angular extent, backward-only growth and image/bearing motion. Use current/past pixels only. Save the raw measurements and provenance; do not replace the frozen Phase 6 channels. Exclude scenario identity and class labels from the extractor API.
3. **Validity audit.** Record empty masks, foreground dominance, multiple components, border contact, near-plane disappearance, timestamp gaps, and insufficient history. Determine these from images/timestamps; renderer diagnostics may audit them separately but cannot supply controller validity flags. Missing evidence is `unknown`, never a fabricated zero velocity or confirmed safety.
4. **Latency audit.** Show earliest available usable measurements, original request time, actuation time, first displacement and stationary contact for danger cases. Separate sensory delay, estimator history and decision delay. Remaining time before stationary contact is not itself a demonstrated safe action margin: acceleration and swept clearance matter.
5. **Identifiability decision.** Report whether the added measurements appear to distinguish the known cases before action is needed, with explicit ambiguity and scale assumptions. No classifier accuracy or generalization claim comes from five geometries.

Do not use action-dependent post-escape frames as evidence that the controller could have predicted danger before its action. Do not train a diagnostic classifier and present its development fit as information proof.

**Stage A output:** `information_audit.md`, source-bound feature/time arrays, a validity report, causal-prefix/reset tests and a go/no-go decision for the prototype. If evidence is insufficient, stop controller tuning and document the missing information or temporal ambiguity. Do not solve an information deficit by supplying world geometry to the controller.

An exact last-safe-request calculation, if needed, is a later evaluator-only diagnostic. Any counterfactual actuator sweeps are new simulation conditions requiring their own manifest, authorization and budget. They are not authorized by the saved-data audit and cannot enter the controller.

## 4. Stage B — implement a small interpretable prototype

Proceed only after Stage A review and authorization of a fully specified candidate rule/calibration manifest. Existing evidence does not justify selecting numerical motion cutoffs, window lengths or score thresholds in this plan. Do not invent them during implementation: document the candidate parameter definitions, units, finite candidate list, selection order, calibration inputs and maximum candidate count before inspecting candidate outcomes. An unresolved field blocks the calibration runner rather than falling back to an arbitrary default.

### B1. Separate image-based feature path

Create a proposed namespace such as `connectome/scripts/collision_threat_v1/`, with new results under `connectome/Results/collision_threat_v1/`. Reuse verified historical snapshots and unchanged world/model primitives. Do not edit Phase 6 encoding, Phase 9 physics, Phase 10/11 source guards or the executed behavioral-v1 sources.

The feature interface returns timestamped measurements, units, validity and reason codes, with no labels or world objects. Keep camera normalization deterministic and frozen; any normalization learned from observations uses development/calibration data only. Start with the existing single-object image domain. Multiple objects and clipping must be detected and reported, not passed through as supported perception. Explicitly specify mask extraction/background assumptions; synthetic known colors do not establish natural-image robustness.

Begin the diagnostic measurements with area-derived apparent radius, normalized centroid displacement from the camera center, horizontal bearing `atan((centroid_x-camera_center_x)/focal_px)`, and angular half-extent `atan(apparent_radius_px/focal_px)`. Derive their first differences from adjacent valid observed frames and their exact elapsed seconds. This initial diagnostic requires no smoothing-window search; any later smoothing or longer history is a separately specified policy parameter. The billboard renderer and radius proxy limit interpretation: these are engineered image measurements, not calibrated retinal angles or physical obstacle distances.

### B2. Threat evidence before neural training

Implement one small predeclared rule combining expansion with image position and motion. Its intended distinction is growing-and-on-a-collision-course versus growing-and-passing. Angular growth together with bearing motion is a candidate, not a guaranteed physical collision oracle. Constant bearing alone is not sufficient proof, and lateral image motion alone is not proof of safety.

The initial rule should emit `threat`, `clear`, or `unknown`, plus interpretable measurements and reasons. Avoid a large heuristic search, broad model competition or thresholds chosen to fix just the known near-miss. If physical-size assumptions are needed, make them explicit protocol assumptions rather than reading actual obstacle radii.

Before policy implementation, `decision_rule_spec.md` must fix the exact score/equations and signs, required valid history, growth/motion/position parameter units, undefined-value handling, persistence, finite candidate values, calibration selection/tie rules and candidate cap. Stage A determines whether such a rule is supported; this plan does not pretend the missing equation or numerical cutoffs have already been validated. Without that reviewed artifact, implement measurements and diagnostics only and leave calibration/behavior dispatch disabled.

Use an expansion-only version of the same new extractor/decision machinery as a representation ablation. This helps distinguish benefit from motion information from benefit due to a different implementation or calibration opportunity. The unchanged legacy feature-only control remains a separate baseline.

### B3. Circuit plus threat gate, with explicit semantics

Retain the circuit and decoder exactly. Log its internal first initiation request independently of physical actuation. The proposed hybrid adds a downstream gate; call it **circuit plus image-based threat gate**, not an improved anatomical circuit.

Recommended composite semantics to lock before runs:

- The circuit's original first request becomes a pending candidate, using its existing latched `escape_requested` output.
- On confirmed threat, a pending candidate may emit the hybrid's first physical request. A clear estimate withholds that physical request but does not erase circuit history or prevent later causal threat evidence from qualifying it.
- On unknown perception after a pending circuit request, the initial conservative policy falls back to the original circuit request. Record every fallback and its outcome. This may retain false alarms in unsupported views; it is not a robustness solution.
- The hybrid's first physical request latches u=0 and starts the unchanged 20 ms delay. No subsequent evidence changes the motor direction or restarts the delay. Preserve the original request time and new physical request time as distinct fields.
- Apply any new evidence-persistence rule exactly as predeclared. Start with the inherited closed 20 ms rule as the proposed default, explicitly record its additional latency, and do not silently tune it after results. Confirm that history can accumulate causally before the circuit request; no retroactive actuation is allowed.

The standalone threat rule requests only on confirmed threat; unknown does not become a threat by default. Its abstentions/misses must be reported alongside hybrid fallback costs. Differences in unknown handling are intentional and visible.

Sensory `unknown` must be distinguished from an integrity or causality defect. Wrong source/model hashes, invalid clocks, nonfinite implementation state or future-frame access abort the run; they never activate the fallback policy.

A downstream veto can suppress false alarms and can delay or lose dangerous escapes. It cannot create an initiation from an always-silent upstream model. Do not attach it to a silent GRU and claim to have fixed that failure. The standalone threat rule is an independent comparator, not a hidden bypass of the circuit.

### B4. Bounded known-fixture comparison

Use the same five already known uniform fixtures and the same neutral actuator for six controllers:

| Controller | Purpose |
| --- | --- |
| No-action | Physical counterfactual and evaluator check |
| Frozen anatomical circuit | Preserved original behavior |
| Frozen legacy feature-only control | Existing simple expansion trigger |
| New extractor with expansion-only rule | Representation/calibration ablation |
| New extractor with expansion plus motion rule | Test the proposed information change |
| Circuit plus image-based threat gate | Test benefit and safety cost of gating initiation |

The proposed cap is **30 unique combinations plus one exact repeat each: 60 attempts**. Aborted attempts count; no automatic retry or added variant. These are new controller conditions on existing geometry, requiring a new protocol and execution authorization. This plan does not authorize them now. Do not extend the previous 182-attempt run or overwrite its results.

The new controllers may receive richer image features than the frozen controllers. This compares engineering pipelines using common raw images and the same motor plant, not neural architectures with matched representations. After different actions, images must reflect each controller's own world trajectory. Use the motion ablation to examine representation effects; do not force identical full observation traces after movement.

All 20 existing eligible GRUs remain preserved reference evidence. Rerunning them is unnecessary for this prototype. If a later comparison includes GRUs, include the entire predetermined eligible roster, including silent members, rather than choosing successful seeds. A richer feature vector cannot be fed to the existing 321-input checkpoints under the old model identity.

## 5. Calibration and independent behavioral validation

The known fixtures and extracted saved traces are already inspected development data. Prototype rule design or new rule calibration using them is explicitly developmental. Reuse cannot create a holdout. Freeze new policy settings in separate artifacts; legacy weights, thresholds and original partitions stay unchanged. The non-GRU silence boundary of 5e-324 is not a new threat score threshold or an established noise tolerance.

Before any broader behavioral calibration/evaluation, prepare a separate protocol containing:

- Target scenario population and exact manifest/generation rules. Cover collision and harmless expansion, lateral passages, static/translation controls, close clearances and different warning times; designate unsupported/multiple/clipped views separately. These are proposed categories, not newly created datasets or geometry values.
- Exact authorized seeds if generation uses randomness; no seed search, redraws or replacement failures. No numerical seed or new scenario bytes are specified by this document.
- Separate development, calibration and independent evaluation families. Keep matched variants, related trajectories and all model runs of a family together. Do not split individual frames or repeated runs across partitions.
- A finite calibration policy and locked model roster, validity/fallback rules, absolute safety/false-alarm targets and paired comparison criteria. Specify any noninferiority margin and uncertainty requirements numerically before evaluation; do not infer them from the current small results.
- Sample count/precision justification and a finite compute/output cap, reviewed before execution. Confidence calculations must use independent world families, not seed or rerun counts.

There is **zero new-world-condition, independent-evaluation or held-out execution budget in this plan**. That stage becomes executable only after its exact protocol and authorization exist. Open-loop benchmark test/OOD clips remain untouched. If policy design changes after seeing independent outcomes, those outcomes become development evidence and cannot confirm the revision.

## 6. Acceptance gates and failure branches

| Gate | Required evidence | If it fails |
| --- | --- | --- |
| Saved evidence integrity | Source/episode/model hashes and selection coverage agree; no production writes | Stop and resolve provenance; never regenerate frozen evidence |
| Causal measurement | Valid units/timestamps, prefix invariance, reset and no evaluator metadata entering controller | Fix implementation before behavior; retain failed logs |
| Information/latency feasibility | Useful image measurements appear available before required decisions, with ambiguity disclosed | Revisit representation, sensing or separately authorized warning-time analysis; do not start a larger GRU schedule |
| Prototype correctness | Exact legacy equivalence and new feature/rule/gate/action tests pass | No episode execution |
| Known-fixture behavior | New candidate preserves all three dangerous successes, requests on neither harmless fixture, and produces no pre-onset escape | Report failure and measured delay/fallback tradeoff; do not claim the problem solved |
| Independent behavior | Predeclared safety and false-alarm targets met on untouched authorized families, with uncertainty and validity coverage | Retain failure; no favorable subset selection or retuning on the evaluation set |

For the development target, report each new candidate whether it passes or fails. Do not select a winning controller and hide the others. A perfect five-fixture result is only permission to consider a broader protocol, never a representative reliability estimate. A gate that suppresses near-miss but causes any known dangerous collision has not achieved the target.

Retain the existing endpoint definitions: evaluator-only stationary-fly danger, first request before stationary contact, no collision/boundary failure through inclusive 1000 ms, and final clearance at least the existing 1 unit. Preserve decision exclusion at 1000 ms. Distinguish internal model initiation, composite physical request, actuation, first motion and actual avoidance. Report dangerous misses, timely-but-failed escapes, harmless requests, harmless movement and movement cost separately. Invalid/unknown perception is retained in the main denominator, not excluded after outcomes.

## 7. Required tests and deliverables

1. **Features:** pixel-only API; current/past timestamps only; growth versus lateral motion; prefix invariance after future-frame changes; time-unit conversion; irregular/gapped inputs; zero/invalid intervals; reset; empty/multiple/clipped/foreground-dominant masks. Synthetic unit images are test inputs, not new behavioral performance data.
2. **Threat rules:** deterministic outputs; stationary, expanding and translating development traces; explicit unknown reasons; no NaN/zero-denominator accidents; expansion-only ablation differs only in approved motion inputs. Class-label/fixture-name changes must not change controller outputs.
3. **Hybrid:** original circuit request retained; pending request can later qualify; clear does not erase history; unknown fallback recorded; additional gate delay measured; first physical event only; no post-contact event, endpoint decision, adaptive direction or restarted delay; silent upstream cannot secretly request.
4. **Legacy equivalence:** preserve the existing 30-test adapter gate and exact numerical outcomes when its source/fixture identity matches. Reuse the original batch-shaped GRU projection/readout mechanism; do not loosen tolerance to accommodate a different arithmetic reduction path.
5. **World and evidence:** delay/acceleration schedule, swept and horizon contact, no-action stationarity, equal pre-action observations, changed future images after motion, separate state schemas, hash/roundtrip checks and exact repeats. Save pre-request/full validity, border/cap/multiple-object flags, unknown/fallback fractions and first invalid time.
6. **Calibration isolation:** reject missing policy manifests, unlocked candidate values, wrong partitions, source mismatch and unapproved evaluation requests. No entry point may silently call Phase 11 training, create missing calibration or resume a partial job.

Suggested modules after approval: `features.py`, `diagnose_saved.py`, `threat_rule.py`, `hybrid.py`, `protocol.py`, `recording.py`, `launch.py` and targeted tests. Reuse existing audited loaders and scheduling contracts through a new wrapper, rather than changing frozen modules. Save the exact execution source catalog, dependencies, environment, policy/model identities, attempt history and before/after preservation inventories. A failed run keeps its records; corrected runs need an explicit identity and consume their authorized budget.

## 8. Compute and operational bounds

| Slice | Proposed cap | Work deliberately excluded |
| --- | --- | --- |
| Stage A saved-data diagnostic | <=91 unique saved trajectories, 15 minutes, 4 GiB RSS, 250 MiB new output | Model fitting/inference, new physical episodes, actuator sweeps |
| Stage B targeted checks | 30 minutes, same process/output limits below | Full historical suites unless a change justifies them |
| Stage B fixture prototype | <=60 attempts, 15 minutes including reporting, 4 GiB RSS, 1 GiB output plus execution snapshot | New geometries, GRU training, full 182-run repetition, parameter search not in its manifest |
| Broader calibration/evaluation or new neural training | 0 until separately specified and authorized | Automatic continuation |

The previous 182 attempts took 134.03 seconds and the worker used about 207.53 MiB peak RSS. Those measurements support a small prototype's practicality but are not runtime estimates for a new extractor or policy. Measure initial authorized work within its cap. Count calibration work within its separately locked finite budget; it is not an unlimited extra activity between stages.

Use `./venv/bin/python -B`, existing dependencies, one worker and the verified snapshot mechanism. Protect the existing worker lease without rewriting production lock metadata. Preserve startup worker/memory/power checks: AC optional with verified battery >=20%, battery check startup-only, disk estimate advisory. Retain thermal/RSS checks and new artifact ceilings. Stop with partial coverage when any execution budget is exceeded; do not alter precision, timestep, roster or cases to fit. No installs, commits, pushes or source-guard bypasses are proposed.

## 9. Decision on training

Do not resume the remaining original trials as part of this work. Keep the partial optimizer/checkpoint/RNG state intact. The two silent GRUs are calibrated outcomes, not evidence of corrupt loading, and a veto does not repair them.

Consider new learning only if Stage A shows usable sensory information and an interpretable baseline exposes a concrete unresolved decision problem. A new neural experiment would need its own behavioral labels/objective, feature/architecture contract, seed/rate roster, training budget, failure handling and separated calibration/evaluation protocol. It is a new model identity, not completion or fine-tuning of the frozen benchmark under its old name. Use the simple rule as the baseline to beat. Do not train until those choices are reviewed and authorized.

Resume the original 120-trial schedule only if the user separately prioritizes completion of its original expansion-discrimination comparison. It remains valuable for that question, but it does not train anatomical weights, revise movement or by itself establish avoidance of unnecessary escapes.

**Recommended implementation sequence:** saved-image diagnostic → review information and timing → lock the small rule/calibration specification → implement and test the rule plus labeled hybrid → at most 60 known-fixture attempts → separately authorize independent behavioral validation. No claim of biological flight, permanent safety, realistic noise robustness or anatomical superiority follows from the prototype.
