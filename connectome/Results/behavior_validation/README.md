# Behavioral validation — implemented engineering comparison

The user authorized implementation and execution of the [bounded proposal](../behavior_validation_planning_20261027/README.md) on 27 October 2026, including implementation improvements within its scope. The original proposal remains unchanged as the pre-execution record. Each execution directory contains its authorization record, exact manifest, code/config/model hashes, checks, attempt history, results and preservation inventories. Earlier frozen phases and the training schedule are unchanged.

## Completed result

[Final report](1793090166386522000/README.md), [full summary](1793090166386522000/summary.json), [saved-file audit](1793090166386522000/saved_file_audit.json) and [preservation record](1793090166386522000/preservation.json).

**Engineering implementation passed; combined behavioral target failed.** All 30 targeted checks passed. The 182 authorized attempts completed in 134.03 seconds of behavioral execution: 91 unique combinations plus 91 exact repeats. Worker peak RSS was 207.53 MiB; its verified input snapshot was 176.79 MB and run output approximately 105.27 MB before final preservation/audit files. All 214,035 protected original files remained unchanged, and all copied execution dependencies retained their hashes. The final saved-file audit independently rechecked all 182 episode hashes and all 91 repeats and added explicit per-frame border/cap/multiple-projection/near-plane diagnostics without new inference or simulations.

The primary circuit and feature-only control each achieved 3/3 dangerous escapes, with 1/2 harmless requests (the near-miss). Eight primary GRUs did the same; seeds 55106 and 55108 retained their silent sentinel and collided on all three dangerous fixtures. No-action collided on all three primary dangers. All ten mapping-55010 GRUs and both active fixed controls succeeded on their two dangerous fixtures; no harmless secondary conditions were run. No active primary controller passed the combined avoidance-and-no-unnecessary-escape target. This is useful implementation evidence and a concrete remaining limitation, not a reliable-avoidance claim.

Attempt provenance is retained: `1793089966941453000` stopped at the sandbox-restricted process-telemetry gate; `1793090022524907000` stopped at exact numerical adapter checks (22 failed, 8 passed). Neither executed behavioral episodes. Their logs, source snapshots where created, failures and preservation records remain visible. The corrected run is `1793090166386522000`; its 30 checks passed before any episode. There was no extra behavioral rerun beyond the approved 182 attempts.

Implementation: [`connectome/scripts/behavior_validation`](../../scripts/behavior_validation). This is a new controller interface and output schema, not a modification to Phase 9 or the open-loop study. It provides anatomical, feature-only, no-action and trained-GRU adapters with a common first-event neutral motor command. The world, camera, 20 ms delay, speed/acceleration caps, finite horizon and collision definitions come from the existing Phase 9 configuration and primitives.

## Scope and execution

The approved manifest has 91 unique controller/fixture combinations and one exact repeat of each, capped at 182 attempts. All 20 selected-and-calibrated GRUs at the planning cutoff are included: ten primary and ten for synthetic mapping 55010. Two selected but uncalibrated GRUs for mapping 55011 and the unfinished trial remain excluded. No extra seeds, fitted thresholds, fixture geometry, world calibration or independent evaluation are introduced. The six-mapping GRU schedule remains incomplete.

The single-worker launcher uses the existing source-verified historical namespace mechanism, copies only required selected/trial/calibration artifacts rather than the 2.4 GiB training/calibration cache, checks startup worker/memory/power/thermal telemetry, and takes the existing training lease without modifying its bytes. The child runs targeted checks before episodes, preserves failed attempts, verifies exact repeats and saved metrics, and enforces wall-time, RSS and output limits. It writes only here; no output is published into earlier phases. Before/after inventories verify the original files and the copied execution dependencies.

Entry point (another full run needs its own authorization):

```bash
./venv/bin/python -B -m connectome.scripts.behavior_validation.launch
```

No dependencies are installed. On macOS, sandbox restrictions may require approval for process telemetry; unavailable worker telemetry fails closed. Startup power policy remains battery >=20% with AC optional; disk estimates remain advisory, distinct from the bounded new-output ceiling. Battery checks are startup-only. Serious/critical thermal pressure and the process RSS limit are also checked during episodes.

## Numerical implementation finding

The initial one-row streaming implementation failed exact equivalence checks despite very small differences: its NumPy/BLAS matrix operations and channel means used a different reduction path from the frozen batch functions. The check gate blocked behavior, and that failed XML/log/source snapshot is retained.

The corrected adapter retains the batch dimensions for independent input projections and readout reductions, while advancing only the actual current hidden state. Current-vector projection padding contains no future observations, predictions or future recurrent states. Projection values are cached only until the current drive changes. The feature control calls the original feature function with the same arithmetic dimensions. The GRU still scores h[k] before applying drive[k], at every millisecond, with zero reset and scale 0.4 once. Exact comparisons cover every eligible GRU's scores and hidden states on saved development traces, causal prefixes, reset, decoder persistence and first-event latch. No equality tolerance, weight, threshold or frozen source was changed to pass.

## Evidence and interpretation

Each successful execution provides:

- `manifest.json`: frozen scenario bytes, complete roster/thresholds, source hashes, action semantics and limits, written before checks and episodes.
- `checks.log` / `checks.xml` / `check_gate.json`: newly executed adapter checks, distinct from historical suites.
- `episodes/`: one NPZ and hashed JSON record per attempt, with explicit GRU-hidden versus anatomical-neuron state identity, causal images/inputs, physical trajectory, decoder traces and endpoint metrics. Stateless controls have zero-width controller-state arrays.
- `summary.json` / `README.md`: per-seed results, separate danger/harmless denominators, combined primary target and limitations.
- `coupling.json`: equal pre-motion images and differing post-motion images for actual circuit versus no-action runs.
- `timings.json`, resource preflight, execution/snapshot records and preservation inventories.

All geometry and endpoint calculations are checked against the saved physical trajectories independently of the controller. A successful engineering run does not mean the combined behavioral target passed. A harmless request remains a false alarm; silence on dangerous episodes remains a miss. There is no favorable-model selection, ensemble voting, motor learning or architecture-superiority claim. The five already known geometries are development fixtures, not an independent sample, and mapping 55010 has no harmless coverage. Sensory validity is retained without excluding invalid episodes. Biological flight, permanent safety, noise robustness and representative generalization remain unestablished.
