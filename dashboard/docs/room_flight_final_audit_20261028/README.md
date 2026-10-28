# Final room-flight implementation audit — 28 October 2026

The task's FastAPI server (PID 7329) shut down completely. Its single port 8001
served the frontend as well. A subsequent process/listener check found no FLY
server on that port and no room launcher. Services remain stopped. No research
simulation, trained-model inference, training, calibration or held-out evaluation
was started in this audit. No dependency installation, commit or push occurred.

The current engineering implementation is ready for its next controlled check;
the research objective is **not yet behaviorally validated**. The latest frontend
was built but deliberately not served or browser-inspected after the stop request.
Build and math/schema tests do not establish visual quality or runtime throughput.

## Requirement review

| Approved requirement | Implementation and evidence | Remaining evidence or separate scope |
| --- | --- | --- |
| A bounded room, floor, ceiling, walls and furniture | Canonical room bounds and solid furniture shared by physics, RGB rays and spectator metadata; opaque cutaway room surfaces, surface seams and the exact furniture volume in Three.js. Six room-face contacts and furniture contact have software checks. | No new room research trajectories yet. The approved room has one furniture volume; it is not a complex furnished household scene. |
| Room visible before a producer runs | New geometry-only default scene imports the exact approved manifest; initial fly pose is labeled design. Room-fitting overview/plan cameras, close follow camera and existing orbit/zoom controls remain. FLY returns an archived view to the design. | No fabricated moving targets, sensor images, neural activity or metrics. Existing explicit episode URLs intentionally retain their historical arena/recording. |
| Genuine front, rear, true left/right and above/below sensing | Body quaternion and six calibrated RGB views; nearest-surface occlusion, body/world transforms, seam association and own-rotation compensation. Six-axis pixel and rotation checks pass. | The first observer explicitly assumes target color and shared sphere size. Arbitrary hands, textures, sizes and compound silhouettes are unsupported. |
| Hover/cruise, repeated escape and recovery | Shared ordinary-motion policy, delayed bounded motor plant, active/recovery/infeasible modes, changing avoidance commands and uncertainty braking. Cruise and repeated-bout software fixtures pass without resetting episode time. | First approved research protocol starts at hover; long sequences, cruise/changed-heading/clutter and sensory-negative research cases require the plan's next exact manifest. |
| Consider every obstacle and room surface | Planner considers all valid visual tracks plus its declared static map, motor queue, delay and acceleration. Exact swept contacts cover spheres/rotated boxes/compound parts and all room faces. No candidate is labeled feasible if its predicted clearance fails. | Constant-velocity predictions, finite candidates and braking under uncertain perception cannot guarantee safety. No arbitrary rigid-body or aerodynamic mechanics. |
| Fair controls and scientific attribution | Ordinary motion, approach trigger and surround avoidance share observations and motor limits. Frozen front-view anatomical activity is diagnostic only. | No anatomical superiority established. A causal panoramic anatomical/GRU sensory adapter requires separate scientific specification and calibration; it is not silently replaced by the conventional planner. |
| Actual live data and synchronized replay | Authenticated producer, body pose, canonical parts, RGB mosaic/view calibration, separate world/decision/neural/image clocks and immutable replay artifacts. Backend rejects missing room pose, incomplete views, changed dimensions/calibration/parts and inconsistent camera clocks. Legacy replay is retained. | Live throughput and research-sized end-to-end operation await an actual room run. The dashboard never starts an experiment. |
| Honest status and sensory support | HUD now reports current room recovery/hover/infeasible/uncertain mode rather than permanently displaying the first escape. Tracking reports supported/uncertain/no-target frame counts and unknown decision fraction separately from frozen encoder domain validity. | No visible target is not proof of empty space. No new sensor robustness or generalization estimate. |
| Durable, bounded execution and failure history | Byte-verified durable snapshot; resource/auth/schema gates before reservation; source/protocol fingerprints; raw computation before audit. Explicit continuation skips all consumed jobs, including failed/interrupted/unresolved reservations, with cumulative elapsed/output accounting in the original run. Resource-block software check proves zero reservation/spawn and preserved-state evidence. | No automatic retry. Budget/resource gates remain active. Continuation logic has deterministic contract coverage; no physical batch was executed to exercise it. |
| Frozen studies and training preserved | All 134 protected source/checkpoint references match the recorded preflight snapshot; the partial checkpoint payload matches its current pointer. Exact approved protocol SHA remains unchanged. | Training remains paused: 45/120 GRUs and 272/816 calibration conditions. Completing those trials does not supply a room motor controller. |

## Changes completed during this audit

- Replaced the room-only-after-recording dependency and translucent box with a
  clearly labeled initial geometry preview and opaque spectator cutaway surfaces.
  Spectator seams/lighting are display finishes; RGB sensors still use the canonical
  unlit scene contract and opaque walls. No new physical furniture or conditions.
- Kept CSS, fonts, colors, HUD layout and existing transport controls. Added room
  framing, genuine 3D aperture guides, all three object coordinates and room mode labels.
- Included focal length in observation calibration checks, strengthened room
  HTTP/WebSocket consistency and added a tracking-support summary.
- Corrected the terminal live packet to report the latest decision mode while
  preserving its separately held camera time, with a focused software check.
- Completed explicit untouched-job continuation and resource-block preservation.
  Previous evidence and approved protocol bytes were retained.
- Corrected current documentation; earlier planning/verification records remain
  historical, including their original approval status.

## Checks actually executed

- Scientific Python: **58 passed** across room and previous avoidance contract tests.
- Dashboard Python: **15 passed** across backend contracts, including in-process
  HTTP/WebSocket tests. One existing Starlette/httpx deprecation warning; no failure.
- Frontend: **13 passed**; TypeScript and Vite production build passed.
- Total: **86 software checks passed**. Tiny deterministic inputs/null or synthetic
  diagnostic data are software fixtures, not research trials or trained inference.
- Protected source/checkpoint references: **134/134 unchanged**, referenced partial
  checkpoint payload matches. Exact initial protocol SHA:
  `0da8016f12627dbc25eef8ca262cabe2245fb0c6a9f0128890f664b7807809fa`.
- No room budget ledger/reservation exists. Previous blocked startup evidence is
  `dashboard/runs/room_1793128531184690000/startup_status.json`: battery 18%, no AC,
  zero reserved attempts, zero simulations. This is historical battery state,
  not a fresh power reading.

## What remains before claiming the requested behavior works

1. On a future requested restart, inspect the built room visually and run the
   already approved eight-scene, three-comparison directional development pilot
   when existing resource gates permit. Keep its 24-attempt ceiling and report
   every collision, unknown/infeasible case, harmless alarm and failed reservation.
2. Use the saved paired ordinary-motion recordings to adjudicate danger and
   harmless encounters. Passing implementation checks is not directional success.
3. After that gate, prepare the plan's separate exact sequence/cruise/clutter and
   sensory-negative protocol (up to 18 attempts); do not invent or run it now.
4. Freeze development/calibration choices before any independently authorized
   evaluation. This audit and the known development scenes are not generalization.
5. Generic hand perception, a causal panoramic neural adapter and biological
   free-flight mechanics remain explicit separate research/model decisions.
   Kinematic yaw and a wing mesh do not reproduce real fly aerodynamics.

There is no defensible overall completion percentage: the engineering room loop
is implemented and contract-tested, while room behavioral success, robustness,
anatomical contribution and biological claims remain unestablished.
