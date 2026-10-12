# Phase 9 implementation plan

## Scope and sequence

1. Verify applicable instructions and Phase 8 completion/freeze/evidence without regenerating earlier outputs. Save SHA-256 inventory of earlier phase files and run earlier tests into Phase 9 only.
2. Review primary research and numerical environment conventions. Record which choices are engineered rather than measured. Save this plan, research notes and a separately versioned closed-loop protocol/config before model outcomes.
3. Implement deterministic planar world, relative-camera circle renderer, bounded delayed escape actuator, swept collision/boundary checks and geometry-only evaluator. Keep world metadata outside the encoder/controller.
4. Connect frame availability at 60 Hz to existing frozen Phase 6 encoding, Phase 4 `dynamics.euler_step`, and Phase 8 `StreamingDecoder`. Encode only new available frame prefixes and keep the existing bounded-history initiation decoder. Verify equivalence with existing batch interfaces; do not copy or change their equations.
5. Define five fixed engineering fixtures (head-on, left, right, static, noncolliding approach). Use primary uniform input for all five and both side fixtures for all five synthetic mapping seeds. Freeze these fixtures before results. Do not select seeds or tune physical/model parameters from outcomes.
6. Test collision roots/tangency/tunneling, actuator delay/bounds/latching, camera geometry, causality, exact frame availability, streamed/batch neural/decoder agreement, saved schema, outcome metrics and replay. Add a scripted action-on/action-off coupling check solely to verify that actions change later pixels; this is not a Phase 10 baseline or a comparative experiment.
7. Save config/source lock, trajectories, stimuli, inputs, full neural/DN traces, actions, outcomes, plots, commands, tests and validation report. Repeat fixed runs numerically; check all earlier hashes and regression results again. Stop at Phase 9.

## Approach and boundaries

Use a small transparent NumPy world instead of installing a game/RL/physics engine. World units are abstract, not millimeters. The fly is a collision disk with a stabilized forward camera; obstacles have disk collision geometry and circular front-facing visual billboards. A first initiation schedules one escape: after fixed delay, accelerate to bounded speed along a backward direction with a latched lateral component from the normalized turn command. Camera does not rotate; this planar translation actuator is not flight biomechanics or yaw control.

Uniform input remains neutral in direction. The five independently documented synthetic mappings retain their names, seeds, gain normalizers and uncalibrated spatial-threshold status. World-rendered observations are a new domain; even the frozen primary open-loop threshold has no confirmed closed-loop calibration. No threshold fitting, held-out benchmark use, H1/H2 test, shuffled/NN control, webcam, anatomical viewer, new dependency, commit or push.

The Phase 5.5 primary task remains untouched. Phase 9 introduces a separate engineering protocol because its collision labels differ from the earlier expansion labels. Evaluate observed finite-horizon survival/clearance and action timing explicitly, without counting harmless episodes as successful escapes. Report false alarms on geometrically safe expanding objects rather than interpreting expansion as guaranteed danger.
