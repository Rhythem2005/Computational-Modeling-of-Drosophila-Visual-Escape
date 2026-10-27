# FLY — finite-body threat and pending-request implementation plan

Prepared 27 October 2026. **Proposal only; no new implementation or experimental execution is authorized by this planning request.** The deliverable is this document, its proposed protocol manifest and evidence fingerprints. Keep training paused and preserve all completed runs. Do not extend the exhausted 60-attempt v1 ledger.

## 1. Decision and lessons

Implement a separately versioned finite-body rule and an evidence-aware hybrid gate before considering more neural training. Test the changes separately as well as together. Passing the current five cases is a regression gate, not completion of reliable behavioral validation.

The [latest prototype](../collision_threat_v1/prototype/1793093607177149000/README.md) completed 60 attempts, including 30 repeats, with 73 passing checks and an independent saved-file audit. Its [detailed findings](../collision_threat_v1/prototype_findings.md) show:

| Observation | Lesson for this plan |
| --- | --- |
| Standalone image-motion rule: 3/3 dangerous escapes, 0/2 harmless requests | Preserve it as a successful known-case baseline; do not claim representative reliability. |
| Circuit hybrid: 3/3 dangerous escapes, 1/2 harmless requests | Correctly suppressing the initial near-miss request did not resolve the full episode. |
| Pending circuit request at 239 ms became a fallback escape at 767 ms, after border contact | An old request should not automatically become a fresh threat when perception is lost. Changing this has a safety cost that must remain measurable. |
| Point-observer rule ignores the fly's radius | Point-clear can be physically dangerous. Fix the geometric model explicitly rather than tune an arbitrary margin. |
| v1 rule and ablation differ in use of image motion | Preserve this representation lesson; 120 expansion-discrimination trials are not the immediate remedy. |
| Past one-row NumPy adapters failed exact equality until arithmetic dimensions were preserved | Reuse exact legacy adapters; do not relax numerical checks or alter frozen sources to make a new test pass. |

Saved-state recheck: 45/120 training trials, 272/816 calibrations; partial trial `train_55011_55102_0p001` remains epoch 51, offset 256, 816 updates, unfinished. The original 20 eligible GRUs remain preserved reference models; two selected-but-uncalibrated records remain excluded. This is a saved-state check, not a new live worker-status assertion.

## 2. Scope, assumptions and the scale problem

The renderer gives `q=[(cx-camera_cx)/r_px, focal_px/r_px]=[relative_x/R, relative_y/R]` for an ideal circular billboard of constant radius R. The point rule tests normalized closest distance against 1. A disk-shaped fly requires contact at:

```
normalized_contact_radius = (R + fly_radius) / R
                          = 1 + fly_radius / R
```

The images alone do not supply R in physical units. Scaling object position, velocity and radius together preserves the projected images, while the fly's fixed physical radius changes the contact relationship. More training cannot be assumed to recover information absent under that ambiguity.

**Recommended initial scope:** an explicitly known-size synthetic environment. Freeze the existing standard object-radius prior `R0=1.5` once, before v2 outcomes, and use the existing self-radius `fly_radius=0.5`. The derived contact boundary is `1+0.5/1.5=4/3`, in object-radius units. This is a geometric consequence of a declared prior, not a fitted threshold or a new motor parameter.

This is a **new information assumption**. Label the candidate “known-object-radius finite-body rule,” not an unrestricted image-only collision detector. The controller receives the fixed prior and self/camera constants, never an episode's actual radius, true position/velocity, fixture ID, danger label or future contact. The evaluator checks the size assumption separately and reports any mismatch. A hidden mismatch must not be silently converted into a different per-object prior.

If known-size assumptions are unacceptable, stop this candidate and prepare a different sensing/size-bound protocol. Bounds on R would imply bounds on the normalized fly radius; no finite conservative bound follows without a positive authorized lower size bound. Do not invent that bound, learn it from evaluation cases, or read evaluator geometry at runtime. Active metric-depth sensing, arbitrary-size objects and extra sensors are outside this initial proposal.

Keep the existing world, billboard camera, neutral u=0 action, 20 ms delay, acceleration cap 400, speed cap 20, 1 ms grid, 60 Hz frames and inclusive one-second physical horizon. No learned movement, adaptive steering, yaw, noise injection or new geometries are included in the initial run.

## 3. Work package A — finite-body rule with one explicit change

Create a new namespace, proposed as `connectome/scripts/collision_threat_v2/`, with new results/attempt ledger under `connectome/Results/collision_threat_v2/`. Leave v1 sources, exact-rule authorization, tests, output and ledger unchanged.

Reuse the v1 causal extractor and normalized position/velocity equations. For each valid adjacent-frame pair:

```
q = [(centroid_x - camera_center_x) / radius_px, focal_px / radius_px]
v = (q_current - q_previous) / elapsed_seconds
t_star = -dot(q,v) / dot(v,v)              # nonzero velocity case
d_star = norm(q + max(0,t_star) * v)
growing = radius_current > radius_previous

point_v1_threat  = growing and t_star >= 0 and d_star <= 1
finite_v2_threat = growing and t_star >= 0 and d_star <= 1 + 0.5/1.5
```

Preserve the v1 stationary, unknown, timestamp and nonfinite-error branches. Retain float64, adjacent observations, no smoothing and the inherited closed 20 ms evidence persistence. The sole rule change in this ablation is the contact radius. Preserve the v1 growth prerequisite and future-closest-approach convention so that this experiment isolates finite-body treatment.

Source review identifies two further limitations to log rather than silently change: non-growing lateral threats can be excluded by the growth prerequisite, and closest approach beyond the one-second evaluation horizon can still trigger a request. Any later revision of those semantics is another declared policy condition. Do not hide either limitation when defining broader evaluation.

Image radius/centroid are rasterized estimates. Inflating by 4/3 handles the modeled body size **under the declared prior**, not measurement error, acceleration or arbitrary objects. Do not call `clear_under_model` a certified safety result. Any numerical tolerances used in tests must be explained as arithmetic checks, not adjusted safety margins.

## 4. Work package B — retire stale requests without erasing circuit evidence

The original circuit decoder remains unchanged and first-event latched. Log its original initiation separately from the composite controller's state and first physical request. The proposed new controller is a **circuit-armed visual threat controller**: after the circuit first arms it, fresh visual evidence can qualify a composite candidate. This is a changed hybrid policy, not a repaired anatomical circuit or proof of a wiring benefit.

Use four explicit pre-action states and no fitted timeout:

| State | Event | Transition/action |
| --- | --- | --- |
| Unarmed | Original circuit first request | Arm once; create a pending composite candidate. Evaluate current sustained evidence. |
| Pending | Currently sustained threat | Emit first physical request; enter Physical-latched. |
| Pending | Currently sustained clear-under-model | Retire that composite candidate; enter Retired-clear. Preserve original circuit initiation in the log. |
| Pending | Unknown perception before retirement | Retain the current conservative fallback: emit first physical request, labeled fallback. |
| Retired-clear | Unknown perception or continued clear | Do not revive the retired candidate or escape solely from its old circuit latch. Record unknown/abstention exposure. |
| Retired-clear | Fresh sustained threat after retirement | Create a new composite evidence epoch and emit first physical request, provided the circuit has armed. |
| Physical-latched | Any later evidence | Log only; do not change direction, restart delay or issue another physical request. |

“Sustained” uses the existing closed 20 ms interval, not a newly chosen lifetime. Separate current threat and clear histories. Unknown breaks both histories and does not count as clear. Re-arming requires a complete new threat-evidence interval after retirement; an earlier ever-latched threat flag cannot qualify it. Integrity/source/clock/nonfinite defects abort, never become a fallback.

At the circuit's arming time, already accumulated **current** evidence may qualify threat or retirement, exactly as the current gate allows current evidence to precede the circuit request. No retroactive physical action is allowed. A historical clear interval that has since been interrupted is insufficient. Record candidate generation/retirement/re-arm times and distinct evidence epochs.

**Safety cost:** after retirement, an unseen changed trajectory may become dangerous while perception stays unknown. Suppressing the stale fallback can then miss a threat. This policy trades behavior under uncertainty; it does not prove “object left view, therefore safe.” Report unknown-after-retirement duration, dangerous failures and lost-observation cases. Do not discard these episodes or claim that the new policy fixes all failures.

A permanently silent upstream model cannot arm this hybrid. Do not add an unlogged standalone-rule bypass to rescue it. Keep that property as a regression test.

## 5. Work package C — bounded factorial engineering comparison

The [proposed manifest](proposed_protocol.json) fixes eight controller roles and the five existing uniform fixtures. It is a proposal, not an executable authorization record.

| Controller | Purpose |
| --- | --- |
| No-action | Check stationary geometry and unavoidable baseline collisions |
| Frozen anatomical circuit | Preserve the original behavior |
| v1 point standalone | Preserve the current successful known-case baseline |
| v2 finite-body standalone | Isolate contact-radius inflation |
| v1 point + original fallback gate | Preserve the observed 767 ms failure |
| v1 point + evidence-aware retirement gate | Isolate pending-request handling |
| v2 finite-body + original fallback gate | Separate body-size effect from fallback policy |
| v2 finite-body + evidence-aware retirement gate | Test the combined proposed change |

Eight controllers × five known fixtures = 40 unique combinations; one exact repeat each gives **at most 80 attempts**, including aborted attempts. This is a separate prospective budget. No v1 ledger reset, automatic retry, extra variant, new seed, threshold search or new world fixture is included. The original feature/expansion controls and GRUs remain saved references; they need not be rerun as new behavioral conditions.

For unchanged conditions, require exact agreement with the saved v1 trajectories and metrics. Give every controller the same causal raw images and camera/motor rules at identical histories. Allow each controller's own action to alter subsequent observations. This compares engineering pipelines with explicitly different information/decision rules, not input-matched neural architectures.

The five known cases will probably be insufficient to expose the finite-body defect: they already pass the point rule. Do not treat another 3/3 as proof that radius inflation helps. Its initial correctness evidence must include analytic/unit cases between the point and finite-body boundaries, then a separately authorized geometry protocol before a behavioral benefit claim.

## 6. Required tests and stop gates

1. **Prior and API:** fixed R0/self-radius validation, physical-unit conversion, invalid/missing prior rejection, no scenario-specific radius lookup or evaluator metadata entering the controller. Verify a new manifest records the side-information assumption.
2. **Finite-body mathematics:** stationary/approaching/receding cases; tangency/contact inclusion; symbolic mid-boundary case `d=(1+4/3)/2`, which the point model clears but the finite model flags; outside both boundaries; scale normalization; undefined and nonfinite estimates. These are synthetic unit calculations, not newly sampled behavioral trajectories.
3. **Perception/causality:** preserve the existing extractor behavior, future-prefix invariance, frame availability, valid history, component/border/gap reasons and resets. Unknown is not zero motion or safety. Do not loosen exact legacy GRU arithmetic.
4. **Gate transitions:** reproduce the original pending-clear-unknown fallback in the old gate; show retirement prevents revival from only an old latch; require fresh sustained threat to re-arm; reject stale historical threat/clear evidence; preserve unknown-before-retirement fallback; preserve silent-upstream behavior; verify fresh episode construction resets all states.
5. **Action/terminal semantics:** one physical event, delay and first movement, no re-aiming, no decision at 1000 ms or after contact, fractional contact precedence and bounded dynamics. Retain actual finite-fly swept geometry and final clearance definitions.
6. **Storage/provenance:** exact repeated arrays/metrics, saved-score/model/source hashes, schema roundtrip, independent geometry/timing reconstruction and complete attempt accounting. Distinguish recurrent neural state, measurement history and gate state explicitly; do not label the full new policy stateless.

Any required test or integrity failure blocks physical episodes. Retain failures. Every reserved episode counts against 80; do not rerun an aborted one automatically or add attempts to recover complete coverage. If coverage is incomplete, report it and conservative success bounds rather than fabricate physical outcomes.

Development acceptance remains: all three dangerous escapes, no request on either harmless fixture and no pre-onset escape, separately for each candidate. Publish the old fallback failure and all factorial cells. A v2 gate that suppresses near-miss but loses a known danger fails the target. The current physical criterion remains a request before stationary contact, survival without boundary/collision through inclusive one second and final clearance at least the existing 1 unit. Harmless survival is not an escape success.

## 7. Metrics and interpretation

Record original circuit initiation; composite pending/retired/evidence-epoch states; current threat/clear/unknown; physical request and reason; fallback, retirement and re-arm events; actuation and first motion; minimum swept/final clearance; collisions, boundary failures and path length. Log known-size prior identity and assumption status separately from evaluator-only actual size.

Keep full and pre-request sensory validity, unsupported-view reasons, clipping/capping, unknown-before/after-retirement durations and fallback-induced harmless escapes in the main report. Do not exclude uncertain episodes to improve results. Report outcomes per fixture/controller; repeats and model variants do not increase the number of independent world families.

No percentage of “project complete” follows from this stage. It can improve a known-case controller and clarify an uncertainty policy. Representative reliability, permanent avoidance, biological flight and anatomical superiority remain outside its evidence.

## 8. Broader behavioral protocol: design first, zero execution budget here

After the engineering gates, prepare a separate exact protocol. Its categories should include finite-fly-only contacts, genuine close harmless passes, matched expansion with different collision courses, loss of perception before and after clear evidence, dangerous motion after a previously clear interval, onset/warning-time variation and the growth/horizon limitations above. If object size varies, specify the new prior/bound/sensing condition explicitly. Categories are requirements, not new scenario coordinates, seeds or generated data.

Before generating/running them, lock the world population, exact condition bytes or generator and authorized seed roster, matched-family grouping, disjoint development/calibration/independent-evaluation membership, controller roster, treatment of unknown/invalid views, endpoint risk tolerances, uncertainty/sample-size justification and compute cap. Keep related trajectories and all their variants in one partition. Never split frames or reruns into apparent independent samples.

Quantitative population acceptance targets and any calibration candidates must be fixed before evaluation. They are not supplied by the five inspected fixtures. Do not silently inherit the open-loop validation FPR limit as a behavioral safety target. No new-world-condition, held-out, OOD or independent-evaluation execution is included in the proposed 80 attempts. Later changes prompted by evaluation require new independent evidence.

## 9. Resources, provenance and approval scope

Use `./venv/bin/python -B`, installed dependencies and one worker. Proposed caps: 30 minutes for targeted checks, 15 minutes for up to 80 engineering attempts/reporting, 4 GiB RSS and 1 GiB new output plus verified snapshot. Prior 60-attempt execution took 31.93 seconds; this is context, not a promise for v2. Measure initial work within the cap and stop on projected overrun without changing timestep, precision, roster or cases.

Retain read-only worker-lease handling, startup memory/worker/power telemetry, battery >=20% with AC optional, startup-only battery policy, thermal/RSS checks and advisory disk estimates. Preserve v1, Stage A, all earlier sources/configurations/freezes and Phase 11 pointers. Record actual new source/dependency fingerprints and before/after inventories in a new execution directory. No installs, commits, pushes, guard bypasses, new training or original-schedule continuation.

**Proposed approval package:** this exact finite-body prior/boundary, the stated evidence-aware state machine, eight fixed controller roles, targeted tests and at most 80 attempts on the existing fixtures. These details are supplied now so implementation can proceed within that scope after approval without inventing a missing cutoff or requiring another routine policy-choice approval. A change to the size assumption, gate semantics, candidate roster, physical plant, condition manifest or experiment budget requires a documented revision. Broader calibration, new geometries and independent evaluation remain separate authorizations.

Implementation sequence: preserve/fingerprint evidence → validate fixed size-prior and derived-radius unit tests → implement the new gate with explicit state/re-arm tests → freeze the v2 manifest → pass legacy/new checks → run the bounded factorial comparison → audit every saved result → propose broader independent validation without executing it.
