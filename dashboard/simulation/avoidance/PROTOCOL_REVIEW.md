# Exact-protocol review required before new research scenes

Implementation was approved on 2026-10-27 with speed work removed. That plan
retained separate approval of exact new conditions and physical/controller
parameters. This is the review handoff, not execution authorization.

## Frozen inherited quantities

World integration remains 1 ms; camera 256×256 at 60 Hz; focal length 160 px,
center (128,128), background/object intensity 128/64, near depth 0.1; self radius
0.5 and declared common object radius 1.5; delay 20 ms, speed cap 20 and
acceleration cap 400 in abstract units. Existing anatomical weights, thresholds,
normalization, decoder persistence and checkpoint contracts are unchanged.

## New quantities to specify and justify

- Exact scenario roster: positions, velocities, motion onsets, object counts and
  every object's radius. Use no new random seeds without explicit declaration.
- Episode horizon: the inherited one second cannot substantiate prolonged
  navigation; any extension is a new experimental condition.
- Vertical bounds for 3D and whether all objects remain within the documented
  stabilized-camera visibility domain.
- Prediction horizon and explicitly enumerated candidate unit directions.
  Prediction is integrated at the same 1 ms step as the physical plant.
- Association displacement and ambiguity bounds in pixels, shape mismatch and
  radius-change limits, maximum observation age and clearance margin. These are
  NEW observer/planner choices, not inherited calibrated neural thresholds.
  They require documented rationale and development-only calibration if fitted.
- Whole-scene versus encounter false-alarm labels; a harmless distractor must
  not be blamed for an escape caused by a different dangerous object.

No placeholder value silently defaults to a working experimental setting.

## Proposed coverage, before numerical specification

1. Two simultaneous left/right approaches and an explicitly feasible lateral or
   vertical escape route; include a conflicting case where the discrete planner
   cannot find a route and must report infeasibility.
2. A dangerous approach mixed with harmless motion; paired harmless-only control.
3. Sequential threats separated by recovery, including a threat on the opposite
   side and a newly appearing object after a prior one retires.
4. Crossing/merging/occluded objects, camera borders and loss of all observations.
5. Actual elevated and lowered threats in 3D, plus floor/ceiling constraints and
   an object obstructing the initially selected escape route.

The exact set is limited to four scenarios × five models = 20 episodes per stage
under the 24-episode ceiling; additional families need a later protocol, not an
implicit larger run. Development calibration and independent evaluation cannot
reuse the same conditions as evidence of generalization.

## Preregistered acceptance and failures

The proposed controller must complete all analytically feasible deterministic smoke cases through their declared
horizon without any fly/object or boundary contact and meet declared clearance.
The proposed controller must have zero avoidance-initiation events in harmless-only smoke cases. Baseline failures are expected observations, not passing claims; execution completion never implies acceptance.
Report mixed-scene alarm attribution separately. No-feasible-candidate, identity
loss, unsupported sensory input, numerical errors and computation/audit failures
remain in the denominator and their artifacts are retained; no favorable reruns.
A failed bounded run is incomplete, not a passing experiment.

Report per-object closest clearance, whole-scene minimum/final clearance, latency
and movement, repeated bout count, tracking uncertainty, sensory-valid fractions,
path length and all commands. Separate reaction timing from transport/display
clocks. Speed improvement is not an acceptance target in this implementation.

Compare no action, simple visual approach trigger, frozen latched retreat, planner
without anatomical permission, and circuit-armed planner under the same plant,
camera rules, starting state and conditions; post-action images diverge causally with movement. Study anatomy's contribution
rather than attributing conventional planner success to the connectome.

## Compute and integrity limits

One worker, no new dependencies, maximum 24 attempts per stage, maximum 30 minutes
and 1 GiB output per stage. Existing battery≥20%, memory, worker and thermal checks
and read-only exclusive lease apply. Each exact protocol consumes a durable
reservation ledger once; failures are not retried automatically. All new artifacts
stay under dashboard/runs. No training, calibration search or held-out evaluation
is authorized by an engineering-development protocol.
