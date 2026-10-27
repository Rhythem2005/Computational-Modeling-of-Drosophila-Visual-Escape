# Interpretation and pending work after v2

## Known-case improvement

The revised retirement gate removes the observed late fallback false alarm while preserving the three demonstrated dangerous escapes. With either point or known-size finite-body threat evidence, it retires the near-miss composite candidate at 239 ms. Border contact produces unknown perception at 767 ms, but the retired candidate is not revived. The original fallback gates still request a harmless escape at 767 ms, reproducing the earlier failure exactly.

This isolates the gate-policy change: both original-gate variants fail on the near-miss and both retirement-gate variants pass. The anatomical circuit itself has not changed or learned to distinguish the near-miss. The new controller is correctly labeled circuit-armed visual threat control.

## Finite-body result

Finite-body contact inflation is implemented under the explicit fixed known-size assumption, using the approved derived 4/3 normalized contact boundary. Analytic/unit tests cover the interval in which a path misses the point but contacts the modeled finite fly, plus contact inclusion, receding/stationary behavior, scale ambiguity, invalid priors and undefined observations.

The five known world cases do not require that correction to pass. Both standalone variants achieve the same observed results, so no finite-body physical performance advantage is established. The controller does not read actual object size or path from scenario metadata; the evaluator separately records prior matches. This does not solve arbitrary-object metric scale estimation or measurement uncertainty.

## Unknown and re-arming are still risks

The near-miss has 233 unknown-after-retirement decision ticks. Those are abstentions under the declared model, not observations of safety. A changed trajectory could become dangerous while the camera remains unsupported. Unit tests establish that fresh sustained threat can create a new evidence epoch and physical event, and that stale threat/clear flags cannot do so. No known fixture exercises a genuine post-retirement dangerous change, so the simulation results do not validate that capability in a broader world distribution.

Unknown before retirement still triggers the conservative fallback. This prevents silently replacing one failure by global suppression of all uncertain escapes. Its safety/false-alarm tradeoff remains to be evaluated on separately specified conditions.

## What is complete

- The exact eight-role, five-fixture engineering comparison, with all 80 attempts accounted for and all 40 repeats exact.
- The finite-body rule and explicit pending/retired/re-armed/physical-latched state machine.
- All 121 targeted checks, including preserved numerical adapters and pre-action driver replay.
- Independent saved-file/finite-fly geometry/timing/gate-log reconstruction; unchanged v1 conditions match cached trajectories.
- Preservation of the scoped scientific artifacts, partial training checkpoint and historical attempt budgets. Dashboard files were excluded and left alone.

## Required next decision

Prepare a separately bounded broader behavioral protocol before running new scenarios. It should include finite-body-only contacts, true close harmless passes, size-prior mismatch or separately declared size/sensing conditions, missing perception before and after a clear estimate, dangerous motion after retirement, different warning times, and the existing growth/one-second-horizon limitations.

Predeclare exact scenario generation/bytes and any seeds, matched-family partitions, development/calibration versus independent evaluation, controller roster, risk/uncertainty targets, sample-size justification, treatment of invalid/unknown observations and resource caps. The current five cases remain development evidence and cannot become independent by renaming or splitting repeats.

No such new cases or held-out evaluation were executed. Do not use new outcomes to adjust a margin, clear-history duration, size prior or fallback policy without a new version and preserved earlier evidence. Keep the original GRU schedule paused unless its original open-loop comparison becomes a separate priority. Completing 120 trials is not demonstrated as a remedy for the remaining behavioral uncertainty.
