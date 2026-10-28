# FLY room-flight implementation plan — 28 October 2026

Status: planning only. No implementation, dependency installation, tests,
training, new simulations or held-out evaluation authorized by this document.
The user's request is to prepare the implementation plan. Speed optimization is
out of scope. Existing dashboard styling and monitoring controls are preserved;
the simulation scene itself must become a room rather than an observation corridor.

## 1. Outcome and scope

Build an engineering simulation in which a fly occupies a bounded 3D room,
maintains a hover or controlled cruising motion, senses an approaching object
from body-front, body-rear, either true flank, above or below, takes an evasive
route that considers the room and other objects, recovers, and responds again.
Directions must be defined relative to the fly's orientation, not the spectator
camera. A true lateral or rear test has its initial relative position along that
body axis; it is not another object placed ahead with a horizontal offset.

The first milestone is biologically inspired behavior with explicit artificial
sensors and bounded motion. It is not a validated reproduction of fruit-fly
flight, a full-brain emulation or an aerodynamic model. A detailed flapping-wing
body and universal biological reaction time are not prerequisites for this milestone.

## 2. Evidence to preserve and learn from

The latest approved multi-object run reserved 20 attempts and produced 18 audited
recordings. The horizontal no-action and vertical frozen-latched reservations
failed before simulation because of a missing temporary snapshot and live-session
capacity, respectively. They remain failed and were not retried. The remaining
no-action danger controls collided. The simple approach trigger and frozen
latched retreat each alarmed in the harmless scene.

Planner-only and circuit-plus-planner each escaped all three dangerous development
scenes and stayed silent in the one harmless scene. Their physical trajectories,
images and initiation events matched exactly in all four scenes. These results
establish no anatomical benefit. They cover a one-second horizon and four selected
scenes, not sustained navigation or independent generalization.

Current limitations are explicit in source:
- `avoidance/world.py` projects only objects at positive relative world Y and has
  no fly orientation. Genuine altitude exists, but sensing remains fixed forward.
- The observer assumes contrast against a uniform background, circular silhouettes
  and a shared known object radius. Textured room walls and an arbitrary hand
  violate that contract.
- The planner uses point estimates, constant-velocity extrapolation, ideal own-pose
  feedback and known bounds. Those assumptions do not become biological sensing.
- The fly mesh has no physical attitude; a drawn wing is not an aerodynamic actuator.
- The fixed neural input adapter is not a calibrated panoramic visual pathway.

Reuse the successful 3D collision/timing, event recording, comparisons and
telemetry work. Preserve all earlier studies, thresholds, seeds, attempts,
checkpoints and original artifacts. Do not resume the 120-trial GRU schedule.

## 3. Architecture and scientific boundaries

Canonical room scene/state -> body-mounted sensor rendering -> causal visual
observations -> object/flow estimates with uncertainty -> behavior selection ->
bounded motor commands -> next room state. The dashboard observes this loop.

The controller may receive declared own-pose/velocity feedback and its own motor
queue. Any known room map is a declared prior, tested separately from map-free
sensing. Obstacle identities, exact positions/velocities, future motions, collision
labels, segmentation truth and time-to-collision truth belong to the evaluator,
not the controller. The renderer may use scene geometry to create pixels; that
is not permission to pass geometry through the sensory interface.

A surround camera rig broadens coverage. Co-located cameras pointing in different
directions do not create stereo depth. Arbitrary object scale remains ambiguous
from monocular images. Retain a declared known-size primitive observer for the
first directional milestone. Add a separate observer before claiming avoidance
of arbitrary hand shapes/sizes. A simulated depth/range sensor may be an explicitly
labeled engineering comparison, never silently substituted for biological vision.

## 4. Work packages and dependencies

### A. Stable execution and scene contract

Create a versioned namespace, proposed `dashboard/simulation/room_flight/`.
Use one canonical scene description for physics, sensory rendering, replay and
the Three.js spectator view. Record object shape, transform, material and actual
collision geometry, room geometry, initial fly pose and all motion scripts.

Move the verified execution snapshot into a durable dashboard-owned location,
or reconstruct it with the existing compatibility mechanism. Verify all bytes
before reserving any physical attempt. Check producer authentication, schema,
viewer cleanup, session capacity and frontend build before reservation too.

Persist every completed computation before post-run audit. Retain partial/error
history, immutable source/protocol fingerprints and a durable attempt ledger.
Failed reservations remain consumed; continuation runs only unattempted jobs.

Gate A: deterministic schema/recording/transport tests pass. No model execution
is necessary to establish basic backend or camera packet compatibility.

### B. Room geometry and body pose

Add a closed room with floor, ceiling and walls, then simple furniture volumes.
Start with geometry whose rendering and swept contacts can be independently
checked. Introduce a hand-like proxy as a compound solid only when collision
support and its observer are ready; a hand mesh enclosing an unrelated small
sphere is not an acceptable research collision model.

Fly state includes world position, linear velocity and a normalized orientation
quaternion. Maintain explicit body-to-world and camera-to-body transforms. Keep
right/forward/up conventions and camera handedness consistent across all systems.

Use reduced-order bounded flight motion first: hover, commanded translation,
controlled heading, active avoidance and recovery. Any yaw/attitude limits and
stabilization rules are NEW model parameters that require protocol documentation.
Do not infer physical roll/pitch from cosmetic animation and then present it as
measured flight dynamics. Gravity, mass, thrust/torque limits and calibrated units
belong to a later physical-model decision.

Gate B: rotation round trips, orthogonal directions, body/world transformations,
wall/ceiling/furniture contacts and high-speed swept contact tests pass. Test
that rotating the fly changes which approach is body-rear while rotating only
the spectator view does not change sensing or decisions.

### C. Surrounding vision and observation history

Implement a configurable calibrated surround rig. An initial engineering profile
can use six directional views with reviewed coverage/overlap; do not describe
this artificial full coverage as biological compound-eye anatomy. A later
biology-informed profile must retain declared blind regions and occlusion.

All views capture the same physical instant; availability and delivery times
are recorded separately. Save calibration, extrinsics, view IDs, body pose and
source pixel frames. Rendering must respect nearest-surface occlusion and the
same geometry shown in the room. Keep the spectator camera outside this sensor rig.

Maintain per-view visual histories, associate tracks in a shared bearing/body
frame and explicitly handle cross-view seams without duplicating one object as
multiple threats. Compensate for known camera/body rotation; distinguish
self-motion-induced image motion from an externally approaching object.

Replace the uniform-background foreground rule before introducing textured rooms.
Develop the observer on declared development conditions. For a known-size
primitive, produce range estimates/intervals under its stated shape prior.
For unsupported shape, scale, overlap or visibility, publish uncertainty instead
of an invented metric position. Loss of a rear object through occlusion is not
proof that the threat disappeared.

Gate C: a direct rear and each direct flank approach appear in the expected
sensor view. Hidden objects remain hidden. Seam handoffs do not create repeated
escape requests. Rotating in a static room does not automatically create threats.

### D. Continuous behavior and collision-aware flight

Separate ordinary locomotion from emergency avoidance. Use explicit modes:
hover/cruise, threat confirmation, active avoidance, recovery and normal motion.
Do not require the fly to remain stationary until an object is introduced.

Select movements using the current valid observations of all relevant threats,
remaining uncertainty, own velocity, motor delay and already queued commands.
Room boundaries and furniture must constrain the same candidate paths as moving
objects. Avoiding one object must not justify hitting another object or a wall.

Steering may change during an active bout; repeated encounters must not reset
neural state, camera history or the episode clock. Recovery needs evidence that
motion and queued commands are safe to terminate. No feasible candidate and
unknown perception must be distinct reported outcomes. Braking under uncertainty
is an engineering fallback, not certified safety.

Freeze an ordinary-motion policy before comparing avoidance controllers. A
minimal cruise/hover policy may be explicit and deterministic; any waypoint
or room map is a declared navigation aid, not a neural discovery. Landing,
walking and takeoff mechanics are excluded from the initial room-flight milestone.

Gate D: rear/side approaches can change the escape direction; a later opposite
threat can elicit another bout without restarting the episode. Confirm recovery
under camera motion, distractors and constrained escape routes.

### E. Anatomical circuit integration without hidden attribution

Preserve the original circuit and encoder as a frozen reference path. The
engineering room controller can first operate with a clearly labeled conventional
surround observer/planner while the original neural trace remains diagnostic.
It must not claim that diagnostic activity caused rear avoidance.

A causal anatomical room controller requires a separately specified sensory
adapter: which views/features drive which of the 321 inputs, normalization,
retinotopic evidence, persistence, reset behavior and calibration scope. Simply
broadcasting a panoramic maximum into the old inputs changes the experiment and
does not establish anatomical spatial coding. Do not add six copies of the
circuit and call them one brain.

Review this adapter separately before enabling a circuit-required panoramic
condition. If the unchanged circuit does not respond to a valid rear observation,
report that limitation; do not silently bypass it while retaining a neural label.
Include planner-only and sensory ablations so anatomy's contribution is testable.
Existing eligible GRUs can remain optional reference models under their existing
selection rules; further training is not required for building the room.

### F. Dashboard integration with the same UI/UX

Keep typography, colors, HUD layout, timeline and existing controls. Replace only
the scene content and necessary data bindings: room surfaces/furniture, actual fly
orientation, all-direction object paths, physical collision shapes and bounds.

Extend the observation contract with versioned quaternion pose, camera-rig
calibration, per-view timestamps/images, declared sensor profile, uncertainty,
behavior mode, command source and event IDs. Preserve legacy 2D/3D replay adapters.
The existing camera panel can show a labeled mosaic/current sensor view without
turning the page into a new dashboard design. Never use the spectator image as
if it were the fly's observation.

Keep live/replay labels accurate. Retain complete science events outside the
bounded display queue; frames may be dropped for viewing, without changing
model time or erasing initiation/collision events. Ended streams release viewers
and remain replayable. Do not automatically start an experiment when a page opens.

## 5. Validation stages, budgets and acceptance

Implementation approval should cover source, deterministic unit/contract checks
and schema integration. New physical conditions still need one concrete exact
protocol review, with numeric values and scenario manifests prepared together
before execution. Do not repeatedly request approval for already authorized
reversible implementation work.

Proposed first run after that review:
- Six single-threat directions, defined in body coordinates: front, rear, left,
  right, above, below. Start with known-size primitives and documented visibility.
- Two harmless controls, including a passing object that does not contact the fly.
- Three primary engineering comparisons: ordinary motion without avoidance,
  simple visual approach trigger with the same motor plant, surround visual
  avoidance. Original circuit activity is diagnostic until its adapter is approved.
- Eight scenes × three conditions = at most 24 reserved attempts, no retries.

Proposed second run, after the first gate and its own locked manifest:
- Four room/sequence/clutter cases and two sensory-negative cases such as rear
  occlusion or cross-view ambiguity, under the same three comparisons.
- At most 18 attempts. Include moving-fly and changed-heading cases; choose exact
  encounter spacing/horizon before observing outcomes. A successful static-fly
  test alone does not establish continuous room behavior.

Each run: one worker, maximum 30 minutes and 1 GiB new scientific output, no new
dependencies without approval, existing power/memory/thermal/worker checks, and
an exclusive read-only worker lease. Profile the chosen sensor/geometry contract
before committing to live throughput. Display lag is reported; reaction-speed
optimization and changes to existing speed limits are excluded.

Record collisions with every object and room surface, per-object swept clearance,
minimum/final clearance, dangerous misses, initiation/movement times, unnecessary
escapes, completed encounters, recovery/bout counts, path length, uncertainty,
sensory support and dropped display frames. Scene truth and reference trajectories
are used by the evaluator only. Near-miss labels must be encounter-specific:
a harmless object present alongside a dangerous one does not make the necessary
escape a false alarm.

For the proposed controller, all preregistered feasible directional smoke cases
must avoid physical contacts and meet their declared clearance; harmless controls
must have zero unnecessary initiation events. Sensory-negative cases must not
be presented as ordinary valid-vision successes. Baseline failures are expected
observations. Report every failed/infeasible/unknown condition and all startup or
numerical failures; execution completion alone is not scientific acceptance.

Longer independent evaluation is a separate stage. Freeze development choices
and calibration before inspecting it, choose sample sizes from the intended
precision/research claim, report intervals and failure denominators, and never
use these development scenes as evidence of generalization.

## 6. Suggested file boundaries

New package under `dashboard/simulation/room_flight/`: `contracts`, `scene`,
`pose`, `sensors`, `perception`, `locomotion`, `avoidance`, `neural_adapter`,
`runner`, `recording`, `evaluate`, `launch`, and focused tests. Keep room protocols
and approvals separate from source. Extend backend telemetry/repository and
frontend types/scene/replay adapters while retaining legacy schema coverage.

Reuse tested world/queue primitives where their assumptions hold; do not edit
`connectome/scripts`, frozen configurations, dataset locks or prior evidence.
Record actual execution source hashes and preserve prior certificates.

## 7. Physics-engine and biological realism decision

Do not install a new engine merely to draw a room. Start with a clearly limited
canonical geometry/pose model and assess whether the required compound solids,
rotations and continuous contacts can be validated with existing primitives.
Before complex hand/furniture dynamics, perform a separate engine feasibility
review rather than growing an untested collision engine. MuJoCo is a candidate
for rigid-body/contact work, not an automatic aerodynamic fly model. An engine
change must include equivalent geometry, timing and endpoint tests and its own
reviewed dependency/resource requirements.

A fly's observed evasive bank/counter-bank behavior motivates future attitude
and flight-model work. Matching those biological trajectories requires data and
model validation; cosmetic bank animations do not satisfy that requirement.

## 8. Source basis

Local: `dashboard/runs/multi_1793122779165392000/analysis.json` and README;
`dashboard/simulation/avoidance/{world,perception,planning,controller,runner}.py`;
backend live/producer contracts and frontend Scene/replay bindings. These were
inspected read-only for this plan. Existing implementation verification records
are historical checks, not new tests executed today.

Primary external sources consulted:
- Muijres et al. (2014), *Flies evade looming targets by executing rapid visually
  directed banked turns*: https://pubmed.ncbi.nlm.nih.gov/24723606/
  Supports directed bank/counter-bank maneuvers, not this model's validity.
- NeuroMechFly vision tutorial:
  https://flygym.readthedocs.io/latest/tutorials/vision_basics.html
  Documents an explicit camera/ommatidia approximation and a chosen limited
  field of view; it does not justify silently labeling an omnidirectional camera
  biological or provide an already validated free-flight controller.
- MuJoCo official overview:
  https://mujoco.readthedocs.io/en/stable/overview.html
  Documents a general physics/contact engine; it is not a fly aerodynamic model.

No runnable protocol, exact new physical parameters, seeds or approval artifact
is created by this plan. The next action after implementation approval is Work
Package A, followed by pose/room and surround-sensor contracts, not another
forward-corridor demonstration.
