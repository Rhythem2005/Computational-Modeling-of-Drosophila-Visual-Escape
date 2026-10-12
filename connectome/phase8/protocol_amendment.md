# Decoder threshold amendment v1.1

ID: `fly_decoder_thresholds_v1_1`. Parent: unchanged `fly_open_loop_v1`, Phase 5.5 protocol v1.0. Scope: the finite threshold candidates for this decoder condition only. Original Phase 5.5 design, manifests, protocol lock, Circuit v2, encoding, dynamics and Phase 7 files remain unchanged.

The human user explicitly approved “Add the versioned improvement” in this chat on 2026-10-11, after receiving the proposal to put finite thresholds just above their training-negative quantiles. This is a local amendment, not external preregistration. Sources/config and parent hashes are recorded before Phase 8 training trace materialization. Prior Phase 6 held-out encoder results have already been inspected in that earlier phase; no Phase 8 held-out neural responses or decisions are inspected here. Later claims must identify this amended condition, not describe it as the literal original protocol.

## Reason and exact change

The original protocol uses `score >= threshold` and raw quantiles of training-negative sustained-score maxima. If every negative is exactly silent, every raw quantile is zero; a zero threshold fires after 20 ms even on silence. The original candidate set then has no feasible finite threshold at the prescribed validation FPR limit, leaving the always-silent sentinel. This consequence is preserved by audit tests rather than hidden.

Use up to 31 equally spaced quantiles from 0 to 1 as before. For each raw quantile q, define the amended finite candidate as `np.nextafter(q, +np.inf)` in float64. Reject overflow/nonfinite candidates instead of substituting values. Equal thresholds are deduplicated, preserving their quantile-index provenance. Keep the separate always-silent sentinel. This changes the training-derived boundary by one representable float and preserves the decision comparison `>=`, 20 ms persistence, no pre-20 ms eligibility, first-decision semantics and observation window. It adds no validation or test normalization, learned weights, margin search or parameter sweep.

Zero backgrounds may therefore yield the smallest positive float64 threshold (about 4.94e-324). That is a numerical silence separator, not a calibrated or noise-robust neural threshold. Do not introduce an arbitrary epsilon to claim greater robustness. This condition is particularly sensitive to tiny positive activity, spontaneous activity and upstream noise; later controls and robustness work are still needed. Duplicate candidates collapse the search budget, not increase it.

## Calibration gate and demonstration

The Phase 6 handoff requires feature-only and linear temporal controls before final decoder tuning. They do not exist yet. Phase 8 therefore creates training-negative candidates and demonstrates the **predeclared highest-training-negative-quantile candidate** as provisional. It does not simulate the validation/test cohorts, choose a validation threshold, or label a provisional threshold as a final calibrated primary model. Final selection must still use the original validation rule (highest timely TPR with full-episode FPR <=0.05; ties smaller FPR then higher threshold), with those controls integrated and documented. Implementing them belongs to later authorized control work.

## Persistence and action interpretation

At regular 1 ms state times, the persistence minimum covers the closed interval `[t-20ms,t]`: 21 sample values represent 20 elapsed intervals. Including the current value ensures a just-observed drop cancels an event; including the left boundary prevents a 19 ms run being called 20 ms. No decision is eligible before 20 ms from episode start. No interpolation or future sample is used. The 1 s diagnostic endpoint is excluded. A first pre-onset decision is latched and cannot be discarded to create a later valid event.

The action is an abstract `escape_initiation_requested` event with an optional time, a one-step impulse, and a latched request. No physical jump, velocity, collision avoidance, flight-state transition or escape success is implemented. Steering is unavailable, represented by null with an explicit reason: uniform visual drive has no calibrated spatial correspondence. DNp02/04/11/06 traces are saved as exploratory activity, never converted to direction or movement. Hemisphere differences alone are not steering evidence.
