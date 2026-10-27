# Exact initial multi-object protocol — pending user review

20 attempts: four 3D scenes × all five predeclared comparison controllers.
No simulations, model inference or training have run for this protocol.
No execution authorization file has been created.

| Scene | Objects and motion |
|---|---|
| Horizontal pair | Left and right objects start at (−6,20,0)/(6,20,0), move at (7.5,−25,0)/(−7.5,−25,0). |
| Vertical pair | Above and below objects start at (0,20,6)/(0,20,−6), move at (0,−25,−7.5)/(0,−25,7.5). |
| Mixed three | The left and above threats plus a near-miss at (0,20,0), velocity (6.25,−25,0). |
| Harmless pair | Static object at (−6,20,0) and the same near-miss. |

All objects have the inherited known radius 1.5. Fly radius is 0.5. Motion onset
is the existing 200 ms. No random seeds. Vertical approaches rotate the existing
left/right geometry into altitude; the combinations and vertical cases are new
conditions, not previously validated evidence.

Keep the existing 1 ms integration, 60 Hz camera, 20 ms actuation delay, speed cap
20 and acceleration cap 400. The initial horizon remains 1 second. The existing
horizontal bounds (−50,50) are proposed for altitude too. These are abstract units,
not biologically calibrated dimensions or wing mechanics.

New, UNFITTED engineering choices requiring this exact review:
- Prediction horizon: 1000 ms, matching the inherited episode duration.
- Candidate directions: the six signed coordinate axes, plus the planner's
  existing zero/current/previous velocity candidates. No change to speed limits.
- Association displacement bound: 24 pixels (9.375% of the 256-pixel image width).
- Association ambiguity bound: 2 pixels; motion association becomes unknown
  when competing matches are too close. This is not a measured noise tolerance.
- Maximum adjacent-frame fractional radius change: 0.5.
- Maximum raster-circle shape mismatch fraction: 0.25.
- Predicted clearance margin: 1 unit, reusing the prior final-clearance target
  as a conservative engineering buffer, not a newly validated safety guarantee.
- Maximum observation age: 17 ms, the ceiling of one 60 Hz camera interval.

These are transparent initial design choices, not values selected from new
outcomes. They have not been behaviorally calibrated. Overlap, silhouette merging,
known-size projection error and field-of-view losses can still cause collisions.
This run diagnoses those limitations; no promise of successful avoidance is made.

Compare no action, simple approach trigger, frozen latched retreat, planner alone
and circuit-armed planner. Same camera/plant/starting conditions; action-dependent
images may diverge. Report every collision, unknown interval, unsuccessful attempt
and harmless request. Success of a conventional planner does not establish an
anatomical advantage. A completed batch does not imply scientific acceptance.

One worker, ≤20 attempts (24 hard cap), ≤30 minutes and ≤1 GiB new output. Keep
battery/memory/thermal/worker checks and preservation hashes. No automatic retries,
held-out evaluation, fitting, GRU training, UI redesign or speed optimization.

Longer navigation, sequential encounters after recovery and statistically powered
independent evaluation remain separate later protocols. This initial one-second
batch cannot establish those claims.
