# Live known-fixture demonstration v1

Authorized by the user's 2026-10-27 request to run the actual simulation live.
This is a fresh engineering demonstration, not a new independent evaluation.

Bound: 15 attempts, no automatic retries, at most 10 minutes and 512 MiB new
output. Five existing Phase 9 fixtures with finite_retirement_gate_v2, followed
by left and right approaches with the original spatial anatomical controller
for all five predefined seeds 55010–55014, in ascending order. No new seeds,
thresholds, world geometries, size priors, controller or motor parameters.

Execution reuses the historical byte-verified v2 snapshot. Every dependency
listed in its snapshot record is checked before and after. Original runner
functions execute unchanged. A Python trace observer reads local values just
before each actual world step, sends telemetry at 10 simulation-ms intervals
and at event ticks, and never changes model/world state. Wall-clock pacing is
0.1× simulation time for visibility; the 1 ms integration and 60 Hz camera are
unchanged. The trace observer and dashboard transport are outside science.
The output records its own actual execution fingerprint and reference hashes.

Use a read-only exclusive worker lease and the existing power, memory, worker
and thermal preflight. Training stays paused. Write recordings, manifest,
attempt reservations, resource samples and checks under dashboard/runs only.
Every attempt must exactly match its saved reference arrays and metrics and
pass independent swept collision/clearance checking. Failure stops the batch.
A saved reference is used only AFTER live computation for verification, never
as the source of a live frame. Persist completed recordings for later replay.

The improved gate moves backward. Directional anatomical demonstrations use
synthetic sensory mappings and all existing predefined seeds; they do not show
adaptive navigation or biological flight. Physics remains planar. Uncertainty,
generalization and biological superiority remain unestablished. GRUs, training,
calibration and held-out evaluation are outside this run.
