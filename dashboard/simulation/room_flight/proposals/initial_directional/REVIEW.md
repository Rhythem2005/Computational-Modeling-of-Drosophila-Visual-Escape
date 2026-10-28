# Exact initial room protocol proposal — not authorized for execution

Eight scenes × three controllers = 24 reserved attempts maximum. This proposal
is prepared for the separate exact-settings review retained in the approved plan.
No authorization file exists; implementation approval does not execute it.

Six true body-axis approaches: front/rear at (0,±20,0), direct flanks at (±20,0,0),
above/below at (0,0,±20), each moving toward the original fly position at speed 25
from 200 ms onward. The last two controls are a static object at (0,20,0) and a
true lateral near-miss starting at (−20,6,0), moving along +X at 25. Object radius
1.5, fly radius 0.5. No randomness or new seeds.

The episode is proposed at 1500 ms (NEW duration) to expose post-escape recovery.
Room bounds are the existing abstract (−50,50) on all three axes. A static table
volume at (12,12,−45) has box half-extents (6,6,4); its exact geometry is given to
all controllers as an explicitly declared static map. It is not an obstacle
position obtained from sensing. Initial fly pose is identity with zero velocity;
ordinary motion is hover for this first directional milestone. Moving-fly cruise,
changed-heading and long encounter sequences need the planned second protocol.

Sensors: six body-mounted RGB views, 256×256, focal length 120 px, synchronized
at the inherited 60 Hz. This gives overlapping engineered coverage, not a claim
about fly eye anatomy. It is a NEW calibration. Material prior: target RGB
(220,60,90), Euclidean color tolerance 8; room RGB (28,42,38). Minimum component
4 pixels; angular silhouette mismatch limit 0.1 rad; range uncertainty 1 pixel;
seam merge bound 0.1 rad; association distance 3 units and ambiguity 0.5 units;
observation gap 34 ms, maximum held-observation age 17 ms. These are transparent,
unfitted starting choices, not calibrated biological or research thresholds.

Heading uses NEW yaw-only rate limit π rad/s. Recovery interval is proposed at
100 ms. Existing integration 1 ms, delay 20 ms, maximum speed 20, acceleration
400, 20 ms persistence, prediction horizon 1000 ms and six candidate axes are
retained. No reaction-speed optimization. Full parameters and motion keyframes
are in protocol.json and will be bound by SHA-256 if approved.

All three models use identical ordinary hover/static-map navigation. Conditions:
ordinary motion without dynamic avoidance; visual approach-trigger retreat;
conventional surround visual avoidance. Optional frozen anatomical activity is
FRONT-VIEW DIAGNOSTIC ONLY, after explicitly uncalibrated RGB-to-grayscale
conversion. It cannot be credited for rear/side escape and cannot veto or trigger
room behavior. The same diagnostic runs in all three conditions.

The observer assumes the shared known sphere radius and target material. It is
not a generic hand/object detector. No sensor depth or simulator object IDs are
passed to control. Unknown/occlusion/infeasibility remain in the denominator.
Candidate clearance is a local prediction with bounded assumptions, not a safety
proof. Human room walls are shown as a cutaway for observation while sensory
rays see opaque physical surfaces.

One worker, 30 minutes, ≤1 GiB output; no automatic retries, training, threshold
fitting, independent evaluation, installs, commits or pushes. Endpoint evaluation
uses the recorded ordinary-motion condition. If that baseline terminates early,
later encounters remain unadjudicated; ambiguous mixed windows never acquire
fabricated false-alarm labels. A completed batch alone does not mean acceptance.
