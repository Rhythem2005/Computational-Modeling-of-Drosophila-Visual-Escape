# Exact candidate specification for reserved Stage B review

**Status: awaiting exact-rule authorization. No policy implementation, rule scoring, calibration or prototype episode execution has occurred.** The approved [implementation plan](../collision_threat_implementation_plan_20261027/README.md), Stage B2, requires this concrete artifact before enabling the prototype. The Stage A implementation explicitly disables prototype dispatch.

## Evidence supporting a candidate

[Stage A report](1793092658671112000/information_audit.md) processed the 91 unique saved trajectories with 23 passing tests. On the five no-action paths, the harmless near-miss first has nonzero image-bearing motion at available tick 217 ms; all three dangerous approaches retain constant bearing while expanding. The frozen circuit requests at 239 ms. This is development evidence that image-motion information is available early, not a new behavioral success result. The original size/growth channels also differ slightly between the cases; the old observations were not exactly identical.

## One analytic candidate, no parameter search

Proposed candidate: `image_constant_velocity_point_observer_v1`. It uses only two adjacent valid observed frames, the Stage A measurements, and the existing camera constants. No weights, thresholds or normalization are fitted. Candidate count is exactly one; calibration, candidate ranking and tie-breaking are not applicable. There is no alternative candidate bank or tuning to a favorable seed.

The following equations assume a single rigid circular billboard of constant unknown physical radius R moving with constant relative velocity over the extrapolation. For a point observer, the pinhole renderer gives:

```
u = (centroid_x_px - camera_center_x_px) / radius_px = relative_x / R
z = camera_focal_px / radius_px                    = relative_forward_y / R
q = [u, z]
v = (q_current - q_previous) / elapsed_seconds
```

R is not supplied to the controller or estimated from a fixture label. It cancels in this normalized representation. Rasterized area-derived radius is an approximation, so the equalities on the right describe the projection model, not exact recovered world geometry.

For valid, contiguous observations:

```
growing = radius_current > radius_previous
if dot(v,v) == 0:
    state = clear_under_model
else:
    t_closest = -dot(q,v) / dot(v,v)
    d_closest = norm(q + max(0,t_closest) * v)
    threat = growing and t_closest >= 0 and d_closest <= 1
    state = threat if threat else clear_under_model
```

The comparison with 1 is the object-radius boundary in object-radius units. It is not a fitted safety margin. Zero defines stationarity, positive growth and future versus past closest approach. No motion deadband, lookahead window, learned score cutoff, absolute pixel-motion threshold, radius multiplier or smoothing parameter is introduced. Arithmetic is float64. Undefined observations produce `unknown`; nonfinite calculations or bad clocks are implementation defects and abort rather than activating fallback.

**Essential limitation:** this candidate treats the fly as a point when estimating threat. It does not recover unknown object scale or account for the finite radius of the simulated fly. A path that misses the point can still hit the fly. `clear_under_model` means only clear under this declared proxy. It is not proof of physical safety. The unchanged evaluator still uses the actual finite-radius fly and swept geometry, and any dangerous miss counts as failure. This limitation must remain prominent in every result and any later protocol. No physical obstacle radius or evaluator geometry may be supplied to fix it secretly.

Constant relative velocity is also an approximation after escape acceleration begins. The first physical action remains latched; post-action proxy estimates do not revise direction. Arbitrary acceleration, multiple targets, natural-image segmentation and realistic 3-D motion are outside this prototype's claims. Development success would not validate those assumptions.

## Perception and missing data

Use exactly the Stage A extractor: known renderer background 128, inherited encoder contrast criterion 4, 8-connected foreground components, one supported component, no border contact, foreground less than half the image. Existing camera dimensions, center, focal length and 60 Hz sampling are unchanged. These inherited values define synthetic-camera perception, not new biological parameters.

Use adjacent frames at their exact timestamps. A missing frame, previous/current invalid observation, or insufficient history yields `unknown`; do not bridge a gap or fabricate zero motion. The Stage A timestamp-gap roundoff allowance of 64 machine epsilons is solely a floating-point scheduling comparison, not a calibrated threat tolerance. Empty images cannot be classified as an object behind the camera.

## Expansion-only ablation

Use the same extractor, validity and adjacent history. State is `threat` iff radius_current > radius_previous; otherwise `clear_under_model`. Invalid/missing evidence yields `unknown`. The ablation removes the closest-approach condition only. It gets no separate threshold fitting or extra cases.

## Temporal decisions and hybrid

- Hold the latest available image-derived state between 60 Hz frames; update only on causally available observations, with no scheduled-onset input.
- Standalone rules emit their first physical request after `threat` holds throughout the inherited closed 20 ms interval (21 samples on the 1 ms grid). `clear_under_model` and `unknown` break that evidence interval. Their absence of a request on dangerous episodes remains a miss.
- For the hybrid, retain the original circuit/decoder first-request latch as a pending initiation. Use current sustained threat evidence, not an ever-latched threat from an earlier interval. A pending request plus currently sustained threat emits the first physical request.
- A pending request plus current `unknown` emits the conservative fallback request immediately, as proposed in the approved plan. Log its reason and timing. A pending request plus `clear_under_model` remains pending; later causal evidence can qualify it.
- Preserve internal circuit request time and physical request time separately. The hybrid is explicitly a circuit plus image-based threat gate, not a modified or learned anatomical circuit.
- The first physical request latches the existing neutral u=0 actuator and existing 20 ms delay. No subsequent direction update, repeated request or restarted delay is possible. Decisions at 1000 ms and after physical termination are excluded.

## Exact proposed bounded comparison

Five existing uniform fixtures only; six controllers: no-action, original circuit, original feature-only, new expansion-only rule, new closest-approach rule, and circuit plus closest-approach gate. Thirty unique combinations, one exact repeat each: at most 60 attempts including aborted attempts. Do not rerun the original 182 episodes, introduce new geometry, retune a candidate or replace failures.

Legacy controls must match their saved trajectories. The new candidates must be reported individually. The development target is unchanged: all three dangerous escapes, no request on either harmless case and no pre-onset escape. Actual finite-radius collisions, invalid perception, unknowns and fallback costs stay in the main report. No held-out evaluation, new-world calibration, neural training, architecture claim or generalization result is authorized by this proposed specification.

Resource caps remain those of the approved plan: one worker, 4 GiB RSS, 30 minutes targeted checks, 15 minutes for at most 60 prototype attempts/reporting, and 1 GiB new output plus snapshot. Battery >=20% with AC optional at startup, worker/memory/thermal gates and advisory disk estimation remain. Stop on integrity, test, execution-budget or causality failure without automatic extra attempts.

## Review checklist

- Evidence review: Stage A measurements precede the old request, while their limits and developmental reuse remain disclosed.
- Mathematical review: normalized projection derivation cancels constant R; no ground-truth path/size is read.
- Scope review: point-observer approximation explicitly fails to guarantee finite-fly safety; the evaluator is unchanged.
- Parameter review: one fixed analytic candidate, no search/calibration, existing camera/segmentation/persistence values only; the geometric 1 boundary and zero sign tests have their stated meanings.
- Semantics review: pending circuit initiation, current sustained threat and unknown fallback have distinct records; physical first-event semantics remain latched.
- Authorization review: **pending**. The code keeps Stage B disabled until this exact specification is approved.
