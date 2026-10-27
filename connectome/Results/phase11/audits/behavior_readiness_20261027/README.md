# Behavioral readiness review — 27 October 2026

## Decision

Keep the remaining Phase 11A training paused while deciding the behavioral-validation objective. There is no new correctness defect requiring abandonment or modification of the frozen discrimination study. However, completing 120 GRU trials is not a prerequisite demonstrated by the repository for making the existing fixed circuit move in the world, and it does not train that circuit or its motor plant. For the user's stated goal of reliable simulated escape, the next useful step is a separately documented behavioral-evaluation plan, not further reassurance based on GRU BCE. No new experiment is authorized or executed by this review.

## What already exists

Phase 9 implements action-dependent observations in an abstract 2-D world. The fixed anatomical rate network and frozen Phase 8 decoder produce a first escape-initiation request. After 20 ms, a prescribed actuator accelerates toward a latched backward/lateral direction, capped at speed 20 and acceleration 400 in abstract units. It does not learn movement, revise direction after the first request, model flight biomechanics, or rotate the camera/body. World positions affect later 60 Hz frames, which become available causally to the 1 ms neural updates.

In saved dangerous fixtures, the first request was at 239 ms, actuation scheduled at 259 ms and first movement at 260 ms. The stationary head-on fly would contact the obstacle at 920 ms. All 13 saved dangerous runs survived the inclusive 1000 ms horizon with the required clearance. These comprise only three dangerous geometries (head-on/left/right) with repeated side fixtures under five synthetic mappings; they are not 13 independent sampled threats. A static fixture remained silent. An expanding harmless near-miss triggered a false alarm.

The saved scripted on/off plumbing comparison independently rechecked equal pre-action frames, 100 differing post-action pixels and 1.09 units of displacement difference. This verifies feedback coupling, not controller efficacy against a baseline.

## Evidence verified now

- All 17 locked Phase 9 source hashes and all 126 delivery artifact hashes matched, using path relocation only for reading historical paths. No frozen file was edited.
- Independently recomputed swept closest clearance, final clearance, path length, first motion, stationary-fly contact geometry, first request and finite-horizon success for all 15 saved model runs. Saved outcomes matched.
- Inspected existing XML: 28 Phase 9 tests have no recorded failure/error. Existing delivery evidence reports 410 total tests and 159 integration assertions historically. No test suite or model simulation was rerun in this review.
- Verified training remains paused and Phase 11 ledger/checkpoint pointers were unchanged. Saved totals remain 45/120 training trials and 272/816 calibration conditions, with the partial trial preserved. No neural inference, test/OOD data evaluation, training, fitting, or new behavior run occurred.

## Why reliability is not established

1. The world cases are preselected engineering fixtures, not a representative independent behavioral distribution. Repeated mappings and bitwise reruns are not new independent evidence. Survival is only through one second; permanent avoidance is not established.
2. The primary near-miss failure shows expansion sensitivity does not establish collision-threat discrimination. There is no sampled harmless-motion false-alarm estimate.
3. Encoder-valid frame fractions range from 71.7% to 100%. Some spatial trajectories leave the frozen single-object encoder's supported image geometry. Outcomes remain visible but cannot be presented as wholly within its validated input domain.
4. World images are a new domain; thresholds are inherited from open-loop calibration. The primary threshold is 5e-324, a positive-versus-zero boundary, not a demonstrated noise-tolerant or biological threshold. No world-domain or independent spatial calibration is established.
5. Both neutral retreat and synthetic turns succeed in these simple danger cases. The evidence does not isolate a benefit of steering or anatomical wiring. The actuator, obstacle paths, stabilized billboard camera and abstract units constrain the interpretation.
6. Phase 9 ClosedLoopRunner directly uses FrozenPipeline, CalibratedDecoder, anatomical weights and selected DN signals. It has no Phase 11 GRU/selected-checkpoint interface. A conventional scalar-output GRU would require a separately reviewed streaming adapter and explicit motor semantics to compare fairly; those are not implemented here.

## Value of the remaining 75 training trials

They complete the predeclared neural-reference comparison across seeds, two rates and five secondary mappings. They provide robustness and reproducibility evidence for open-loop discrimination. They do not update the anatomical network, train escape actions, remove near-miss false alarms, validate clipped frames, or establish collision avoidance. Existing trained weights remain usable reference artifacts. The incomplete schedule must remain explicitly incomplete; do not relabel it complete or select favorable seeds.

## Next decision, before execution

Prepare a separately versioned, bounded behavioral-evaluation proposal using the existing environment and preserved models. Its predeclared endpoints should distinguish successful dangerous avoidance, harmless false alarms, collisions, latency, encoder validity and finite-horizon limitations. It should specify fair no-action/simple-trigger controls, common actuator/observation rules, scenario partitions, model inclusion/failure handling and acceptance criteria before inspecting any new outcomes. Determine whether the existing circuit suffices as the initial controller; do not require all GRU trials without a concrete comparison purpose. A GRU comparison, if included, needs an explicit causal adapter with verified timing and state reset.

This is a list of unresolved requirements, not a new protocol, selected scenario set, parameter change or permission to evaluate held-out data. Keep earlier freezes, thresholds, seeds and Phase 11 schedule untouched. Later execution, calibration changes, new fixtures and Phase 12+ work require separate authorization. If the user instead wants the original full research benchmark, resume the existing frozen schedule after explicitly accepting its purpose and compute cost.

## Repository sources inspected

- connectome/Results/phase9/protocol.md and environment_config.yaml
- connectome/scripts/phase9/runner.py, world.py, activity_io.py, config.py
- connectome/Results/phase9/results/definition_lock.json, delivery_artifact_index.json, validation_report.md, delivery_verification.json, saved episodes and coupling evidence
- connectome/scripts/phase10/models.py and connectome/Results/phase11/training_plan.md

Machine-readable verification and the read-only verification script accompany this report.
