# Finite-body and evidence-retirement v2 — completed engineering comparison

Implemented the user-approved [plan](../finite_body_gate_plan_20261027/README.md) in a separate `connectome/scripts/collision_threat_v2/` namespace. Earlier versions, anatomical weights, calibration thresholds, source-compatibility guards, movement rules and training checkpoints are unchanged. No dashboard files were read or modified as part of implementation; dashboard filenames were excluded from preservation scope.

## Result

[Full run report](runs/1793096608346990000/README.md), [per-controller/episode summary](runs/1793096608346990000/summary.json), [saved-file audit](runs/1793096608346990000/saved_file_audit.json), [test log](runs/1793096608346990000/tests.log), [preservation record](runs/1793096608346990000/preservation.json), and [detailed interpretation](findings.md).

| Condition | Dangerous escapes | Harmless requests | Known-fixture target |
| --- | --- | --- | --- |
| Original anatomical circuit | 3/3 | 1/2 | FAIL |
| Preserved point standalone | 3/3 | 0/2 | PASS |
| Known-size finite-body standalone | 3/3 | 0/2 | PASS |
| Point + original fallback gate | 3/3 | 1/2 | FAIL |
| Point + revised retirement gate | 3/3 | 0/2 | PASS |
| Finite-body + original fallback gate | 3/3 | 1/2 | FAIL |
| Finite-body + revised retirement gate | 3/3 | 0/2 | PASS |

No-action remained stationary and collided on all three dangerous cases. The revised gates retired the near-miss candidate at 239 ms and did not revive it when perception became unknown at 767 ms. Each retained all three dangerous escapes. Unknown-after-retirement exposure was 233 decision ticks on the near-miss and remains reported as uncertainty, not proven safety.

All **121 targeted checks passed**: the 73 preserved legacy/v1 checks plus 48 new v2 analytic, state-machine and saved-prefix integration checks. All **80 approved attempts** completed: 40 unique combinations and 40 exact repeats. Episode execution took **48.52 seconds**, with measured worker peak RSS about **241.05 MiB**. The separate saved-file audit checked all 80 physical trajectories, 40 repeats, 40 unchanged v1-reference episodes and 20 revised-gate timelines. The 214,794 scoped scientific files and active v2 source catalog remained unchanged during execution. The dashboard was not included in this inventory.

## What changed

- Finite-body variants use the explicitly approved fixed object-radius prior 1.5 and self-radius 0.5. The normalized contact boundary is `1 + 0.5/1.5 = 4/3`. No per-episode true object radius enters the controller. Evaluator metadata separately confirms the prior matches these fixtures.
- The revised gate retains the original circuit first-request record but retires a pending composite request after current clear-under-model evidence persists through the inherited closed 20 ms interval. Unknown perception cannot revive that retired request.
- Fresh sustained threat after retirement may re-arm a new evidence epoch before the first physical escape. This behavior is covered by unit/state-machine tests; there were no re-arm events in the five known world fixtures.
- Unknown before retirement retains the conservative fallback. The first physical request remains latched, neutral and subject to the original plant/delay. No anatomical weight or motor learning occurred.

## Limits

These are the same five development geometries already inspected. They do not establish generalization. They already pass the point rule, so the comparison does not establish a finite-body behavioral advantage. Analytic mid-boundary tests verify the intended geometric change; new physical grazing/contact cases need their own protocol and authorization.

The finite rule needs a correct object-size prior and still uses quantized images, a circular billboard and constant-relative-velocity extrapolation. The growth prerequisite and future-closest-approach convention retain their v1 limitations. Retiring an old request can miss a newly dangerous unseen trajectory; lack of a fallback is not proof that losing an object is safe. No biological fidelity, wiring superiority, realistic noise tolerance or permanent safety claim follows.

## Evidence and operational scope

The [authorization](authorization.json) binds the exact plan and [proposed condition manifest](../finite_body_gate_plan_20261027/proposed_protocol.json), including the parallel-dashboard exclusion. The locked run manifest precedes new tests and episodes. The verified snapshot retains original file bytes and the documented historical namespace, including exact operational source certificates. Scientific preservation uses a fixed earlier-artifact filename list, not a broad scan of new dashboard/frontend/backend files. Generic top-level project README changes are outside that inventory; frozen execution still uses its verified archival README.

The [v2 attempt ledger](runs/attempt_ledger.json) is exhausted at 80. The earlier v1 ledger remains exhausted at 60 and was not extended. Another launcher invocation refuses extra attempts; do not reset either ledger. The invocation was:

```bash
./venv/bin/python -B -m connectome.scripts.collision_threat_v2.launch
```

That command is recorded for provenance, not permission to rerun the completed comparison. Targeted tests and final audit stayed within the declared resource budget. All outputs are in this new namespace; no original training/result publication path is used. No dependency installation, commit, push, calibration, new geometry, GRU training or held-out evaluation occurred. The original schedule remains paused at 45/120 completed trials and 272/816 calibrations; the unfinished checkpoint is preserved.
