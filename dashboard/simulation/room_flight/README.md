# Room-flight implementation

Approved implementation of the 28 October room-flight plan, isolated under
`dashboard/`. Frozen scientific source, studies, checkpoints and thresholds are
untouched. Existing HUD styling/layout and controls remain; room geometry, body
pose and the actual sensor mosaic are new data bindings. No new dependency.

## Implemented

- `pose.py`: normalized XYZW quaternions, body/world/camera transforms, shortest
  quaternion interpolation and bounded yaw-only heading dynamics.
- `geometry.py`: canonical spheres, rotated boxes and compound solids. Pixel rays
  and finite-body swept contacts use the same parts, transforms and dimensions.
  Sphere/box contact includes rounded corners instead of an inflated-box shortcut.
- `world.py`: delayed bounded 3D velocity actuation, body heading, room boundaries,
  furniture and scripted piecewise-linear object motion. No wall tunneling or
  silent respawns. Objects can approach from actual lateral/rear/vertical axes.
- `sensors.py`: synchronized calibrated body-mounted RGB views. Six-axis helper
  supports engineered surrounding coverage. Occlusion is real nearest-surface
  occlusion; the observer receives no depth, object IDs or scene state. The
  human-facing room is a cutaway; camera pixels see opaque physical room surfaces.
- `perception.py`: explicitly declared target-color/shared-sphere-size prior,
  angular silhouettes, range intervals, conservative seam association, generated
  track identities and own-motion compensation. No arbitrary-shape hand detection
  or biological compound-eye claim. Hidden or uncertain objects are not declared safe.
- `locomotion.py`: ordinary hover/cruise and known-static-map navigation shared by
  all conditions, approach-trigger baseline, repeated surround avoidance bouts,
  recovery, uncertainty braking and explicit infeasible candidate reporting.
  The conventional planner never accesses dynamic object truth or future scripts.
- `neural_adapter.py`: optional frozen FRONT-view anatomical diagnostic, with
  explicitly new RGB-to-grayscale preprocessing. It is not the surround motor
  controller, never grants rear-escape permission, and is labeled unvalidated in
  this new sensory domain. A causal panoramic neural adapter remains separate work.
- `runner.py`: causal multi-view histories, 1 ms decisions, physical/camera/neural
  clocks, commands and event evidence. Terminal pose can be recorded without a
  terminal decision. Full RGB view stacks and mosaic are preserved independently
  of display transport.
- `recording.py`: computation saved before audit; independent traversal of saved
  contact segments, bounds, speed, acceleration and heading limits. Only audited
  pairs enter the archive. Per-encounter task labels are adjudicated against the
  recorded ordinary-motion condition. Missing/early-terminated counterfactuals
  and overlapping threat windows remain unresolved, not fabricated false alarms.
- `execution.py` and `launch.py`: durable byte-verified historical namespace,
  initial-geometry/schema/authentication checks before reservations, worker lease,
  original resource gates, exact protocol approval, bounded attempt/time/output
  ledger, actual execution fingerprints and source/checkpoint preservation.

Backend accepts RGB mosaics, body quaternion and per-view timestamps/images.
Legacy grayscale/2D/3D replay remains supported. The frontend displays canonical
room/compound geometry, actual orientation and a labeled sensor mosaic using
existing panels. New API `producer/check` authenticates and checks capacity
without starting a session, inference or simulation.

## Deliberate limits

This is bounded translation with kinematic yaw, not gravitational or aerodynamic
flight. Wing appearance is not a force model. Compound hand-like solids can be
rendered and collided, but the first visual observer assumes target color and
known-size spheres; generic hand/texture perception is not established. A known
static map and ideal own-pose feedback are explicit engineering priors. Views
pointing in different directions do not supply stereo depth.

No free-flight research episode or trained-model inference has been run for this
implementation. Tests use tiny deterministic algorithm fixtures and a null neural
diagnostic only. They establish software contracts, not six-direction escape
performance or biological validity. No training or held-out evaluation ran.

The exact first directional protocol under `proposals/initial_directional/` was
approved by the user and is SHA-bound by `authorization.json`: eight scenes ×
three comparisons, at most 24 attempts. The earlier launch stopped before any
reservation at the existing battery gate (18%, not connected to AC). No room
research episode has executed. The server was stopped at the user's request.
See [final implementation audit](../../docs/room_flight_final_audit_20261028/README.md)
for current checks and the remaining validation stages. Earlier verification
artifacts retain their historical status and are not rewritten.

The frontend now has a geometry-only room preview before any producer runs. It
imports the approved room bounds, static collision volume and initial fly pose;
it does not create sample trajectories, camera frames, decisions or results.
Opaque spectator cutaway surfaces, floor/wall seams and room-fitting cameras
replace the old arena for room sources. Original styles and HUD layout remain.
Click the FLY brand to return from an archived episode to the room design.

Calibration checks now include focal length. Room ingestion requires normalized
body pose, the complete calibrated sensor set, exact image dimensions and a
shared camera clock. Tracking support/uncertainty fractions are reported separately
from the frozen encoder's unsupported sensory domain.

Explicit continuation with `--continue-record <original-room-run-directory>` can
execute only untouched jobs. Failed/interrupted/unresolved reservations remain
consumed, duplicate jobs are rejected, and elapsed-time/output accounting uses
the original run. No retry or continuation starts automatically. Resource-blocked
startup preserves protected-state evidence before returning without reservations.

Run explicitly with the existing scientific Python:

```
./venv/bin/python -B -m dashboard.simulation.room_flight.launch \
  --protocol APPROVED_ROOM_PROTOCOL.json --authorization APPROVAL.json \
  --snapshot-record VERIFIED_HISTORICAL_RECORD.json
```

Use `--live` only after restarting the updated backend supporting API 1.2 and
supplying the environment-only producer credential. The dashboard does not start
experiments on page load. No server or research simulation was started during the final audit.
