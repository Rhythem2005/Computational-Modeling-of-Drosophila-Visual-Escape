# Closed-loop engineering protocol v1.0

This is a new Phase 9 condition, `fly_closed_loop_engineering_v1`, authorized by the user's request to implement Phase 9. The original `fly_open_loop_v1`, previous phase files and Phase 8 calibration remain unchanged. Lock definitions before world-model outcomes. No behavioral/model tuning or confirmatory experiment is performed here.

## World, observation and actuator

World x increases right and y increases forward; time is in seconds for geometry and ms for neural/decision grids. World units are abstract. A radius-0.5 fly begins at [0,0]. Collision obstacles are disks, radius 1.5 in standard fixtures. Bounds are [-50,50] on each axis; touching the fly's permitted center boundary is a boundary failure. Obstacles may enter/leave bounds. Motion begins at 200 ms with fixed per-obstacle velocity; within each 1 ms interval world trajectories are straight segments. Fly speed is constant during a segment, then increases by at most acceleration*0.001 to its cap. This discrete world definition makes swept collision exact for each modeled segment.

A stabilized +y camera projects each forward-facing circular billboard from relative position: `cx=128+160*relative_x/relative_y`, `cy=128`, radius `160*obstacle_radius/relative_y`. Depth <=0.1 is invisible; near-plane disappearance is counted in diagnostics and never treated as proof of safety. Rasterize with the existing Phase 5 hard circle renderer, back to front, into 256x256 uint8 frames with background128/object64. This is a pinhole-style billboard approximation, not anatomical retinal projection or a real sphere image. Multiple silhouettes/edge clipping remain unsupported by the frozen single-object encoder; report encoder validity rather than changing it.

At the first initiation, latch normalized turn u in [-1,1]. After 20 ms, start the escape acceleration profile, capped at 20 world units/s and 400 units/s². Latched velocity direction is `[sin(theta),-cos(theta)]`, `theta=u*60°`: zero retreats backward; positive requests a rightward lateral component. There is no body yaw, camera rotation, motor biomechanics or command adaptation. With speed0 at activation, the first nonzero displacement starts in the following 1 ms segment. Later requests cannot change direction/delay. Future phases may compare separately versioned plants; never tune this one to rescue decoder results.

## Causal scheduling and frozen model

At neural time k ms, only rendered frames at exact timestamps `n/60 <= k/1000` are available. A frame at 16.666… ms first affects the 17 ms neural update. Fractional frames are rendered from the world segment at their own physical timestamp, then become available at the next eligible integer tick. Use strict comparison, no epsilon that exposes a future frame.

Process new available prefixes through unchanged Phase 6 encoding (or named Phase 8 synthetic field weighting), read existing neural state x[k], update the Phase 8 streaming initiation rule, latch a motor command on the event, then advance the world segment and existing Phase 4 Euler state. Input scale0.4 applies once. Keep zero initial state/bias/noise, tau10/gain0.5/dt1/clip50 and frozen IDs/order/normalization. Decisions at t=1000 are excluded; physical contact at the inclusive 1000 ms boundary counts as collision. On earlier contact stop the world exactly; no decision after termination and no full-grid neural state beyond it is saved. A completed-step endpoint state is diagnostic, not an extra decision.

Render observations from actual action-dependent world positions. Geometry/config/labels enter only the world and evaluator; controller inputs are frames/timestamps and neural states. Re-encode only when a new frame becomes available; retain causal prefixes for bitwise agreement with the frozen batch encoder. No new normalization or threshold fit.

## Fixed fixtures and interpretation

All fixtures have one radius1.5 object at y20, with x=0 for head-on or x=-6/+6 for left/right approaches; approach velocity `[-x/0.8,-25]` targets origin at1s. Static uses [0,20] and zero velocity. Near-miss uses [0,20] and velocity[6.25,-25], targeting[5,0]; it expands but does not collide with a stationary fly. All use motion onset200 ms. Save primary uniform runs for all five fixtures and left/right synthetic runs for every seed55010..55014. These are fixed engineering fixtures, not sampled train/validation/test families. No tuning or favorable-seed selection. Same world fixtures across seeds intentionally isolate mapping changes.

Uniform primary is directionally neutral. Synthetic spatial initiation reuses its previously uncalibrated threshold and mapping. The world domain also lies outside primary open-loop calibration. Report these as integration runs, not final calibrated behavioral-model results. Verify action-to-future-frame coupling with a separately labeled scripted on/off plumbing fixture, without architecture comparison.

## Metrics and outcomes fixed before results

Evaluator-only `danger`: a stationary initial fly would contact an obstacle during [0,horizon], determined analytically from the obstacle's onset and path. This counterfactual is a geometry label, not a controller input or learned baseline.

Record first initiation, pre-onset flag, onset-relative latency (None for absent or early request), scheduled actuation time, first motion time, collision/boundary time and object ID, minimum swept clearance, final clearance, path length, normalized turn, and truncation versus termination. Minimum clearance includes closest approach within every modeled segment; contact is center distance <= sum of radii. Collision wins a simultaneous horizon contact; an initial overlap is terminal at zero. Boundary contact is failure even if no obstacle contact occurs.

`survived_horizon` means no collision/boundary failure through the finite inclusive horizon; it is not permanent safety. `escape_success` is defined only for danger fixtures: a request was made before the stationary-fly contact time, the actual world survived its horizon, and final obstacle clearance >=1. Otherwise it is false; for harmless fixtures it is None. Report dangerous misses explicitly. A request in a harmless fixture is a false alarm, including an expanding near-miss. No success-rate inflation from harmless episodes. No aggregate balanced accuracy, H1/H2 test, behavioral superiority, RL reward, later control networks or statistics are implemented.
