# Multi-object avoidance implementation

New, separately versioned engineering controller. All files are under dashboard;
the frozen circuit, prior studies, scientific configurations and results are untouched.
The existing dashboard layout, styles and controls are retained. Only position/data
bindings, truthful labels and physical altitude/floor placement have changed.

## Implemented

- `world.py`: bounded-acceleration 2D/3D motion, delayed motor-command queue,
  multiple independently moving objects, finite fly/object bodies, swept contacts,
  floor/ceiling/wall boundaries and action-dependent perspective camera images.
  Coordinates are X right, Y forward, Z up. The camera is stabilized; the objects
  use known-radius billboards. This is a kinematic engineering model, not wing,
  gravity, banked-turn or aerodynamic simulation.
- `perception.py`: foreground components and conservative visual association,
  known-size relative position/motion estimates, explicit border/shape/merge/gap/
  lost-track ambiguity. It accepts only pixels and camera time. Track identities
  are generated internally; simulator IDs never enter perception or planning.
- `planning.py`: enumerate reviewed candidate velocities and evaluate their
  acceleration-limited paths against every valid object estimate and the bounds,
  including commands already queued and the original actuation delay. Tangency
  is contact. No predicted feasible choice is reported explicitly. There is no
  guarantee outside the constant-velocity/known-size/observable domain.
- `controller.py`: per-track closed-interval 20 ms threat persistence, original
  circuit first-event arming, active steering, recovery, subsequent escape bouts,
  braking under unknown perception and explicit infeasibility. Neural state is
  preserved throughout an episode. No stale unknown fallback is reintroduced.
- `circuit.py`: existing FrozenPipeline, encoder, anatomical Controller and
  calibrated threshold APIs in a byte-verified historical snapshot. New images
  are a new sensory domain: frozen weights do not establish multi-object or
  vertical tuning. No GRU training, checkpoint modification or fitting.
- `telemetry.py`: bounded asynchronous observation queue. Scientific stepping
  does not wait on network publishing. Display samples may be dropped, events
  are carried forward and full-resolution scientific recording is separate.
- `recording.py`: save computed NPZ and JSON before auditing; independently
  traverse saved physical segments; publish a catalog pair only after checks.
  A failed post-run audit retains the computation and error history.
- `runner.py`: causal camera availability, 1 ms neural/controller schedule,
  first-event timing, separate terminal physical/neural/decision clocks,
  full trajectory, tracking, commands, sensory validity and metric evidence.
- `cli.py`: exact protocol-byte authorization, all five fair comparisons,
  per-protocol attempt reservations, no automatic retries, resource preflight,
  read-only worker lease, source/checkpoint preservation and bounded output/time.

## Comparisons

`no_action`: no motor commands. `simple_trigger`: sustained visual approach
produces one neutral retreat. `frozen_latched`: frozen circuit initiation drives
one neutral retreat. `planner_only`: tracked collision threats drive the new
planner without the circuit permission. `circuit_planner`: the circuit's one-shot
initiation arms the separate per-track planner; subsequent bouts retain that
permission and do not reset the circuit. This is explicit engineering arbitration,
not a newly discovered anatomical navigation mechanism. All five use the same sensory contract, neural diagnostic, tracker and physical plant. Their post-action images differ causally with their movements.

## What was deliberately not changed

No speed optimization or reduction of the original 20 ms persistence/actuation
rules. Original speed 20 and acceleration 400 remain inherited limits. Historical
training/selection/calibration rules and studies retain their original meaning.
No dependencies were installed. No dashboard redesign, commits or pushes.

## Review before research execution

`proposals/2d.review-template.json` and `3d.review-template.json` copy inherited
constants and intentionally leave new association, uncertainty, planning and
vertical-bound choices unresolved. They contain no executable research scenes.
They cannot run. See PROTOCOL_REVIEW.md for the exact remaining design decisions
and acceptance criteria. New geometry, thresholds, a longer horizon and vertical
parameters need the separate protocol review retained by the approved plan.

No new multi-object research scenes, independent evaluation or live experiments
were run. Deterministic algorithm unit inputs and a zero-output test double check
software contracts only; they are not research performance results.

Once an exact manifest has been separately approved, supply its SHA-256-bound
approval JSON (`status=APPROVED_EXACT_PROTOCOL`, `episode_cap=24`,
`training_authorized=false`, `held_out_authorized=false`) and the original verified
snapshot record. From the repository root the explicit command is:

```
./venv/bin/python -B -m dashboard.simulation.avoidance.cli \
  --protocol APPROVED_PROTOCOL.json --authorization APPROVAL.json \
  --snapshot-record VERIFIED_SNAPSHOT_RECORD.json
```

Add `--live` only with an already running API supporting the new 3D telemetry
contract and an environment-only FLY_DASHBOARD_INGEST_TOKEN. The UI/backend never
launch an experiment automatically. Rebuild/restart the backend as needed when
that separately approved live run is prepared. Do not reuse the old closed demo
launcher to bypass protocol review.

## Research limits

Known object radius and constant-velocity visual prediction are explicit priors. The controller receives ideal proprioceptive fly pose/velocity, known arena bounds and its own actuator queue; it receives no obstacle ground-truth positions or future paths. The single stabilized camera has blind regions and is not a compound-eye model.
Merged, hidden, rearward, cropped and ambiguous objects cannot be certified clear.
The policy brakes and reports unknown; this can still collide. Candidate-search
infeasibility is not a proof that no physically possible escape exists. All-object
stationary-fly danger and whole-scene false alarms are reported separately from
per-object encounter attribution, which still requires an evaluator protocol.
Full aerodynamic flight, calibrated biological units, anatomical superiority and
independent generalization remain unestablished.
