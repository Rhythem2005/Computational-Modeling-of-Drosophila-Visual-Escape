# Phase 8 decoder specification 1.1.0

Purpose: turn simulated descending-neuron activity into a causal, abstract escape initiation request. Implement the supported initiation part of the roadmap, without starting the environment, action physics, behavioral evaluation, baselines, experimental comparisons or visual demonstrations from later phases. Directional steering remains gated on spatial evidence.

## Preconditions and frozen components

Read the unchanged Phase 5.5 protocol and Phase 6 handoff, and verify Phase 7 saved source/config/artifact hashes and passing evidence. Establish before/after inventories and rerun earlier tests with evidence routed into Phase 8. Do not call validators that write into earlier phases. Use `./venv/bin/python`, existing NumPy/PyYAML/Matplotlib/pytest, and no new dependencies. Keep Circuit v2, body-ID order, encoder normalization/config, simulator dynamics and 1 ms step unchanged.

The explicitly approved [threshold amendment](protocol_amendment.md) is a new local condition `fly_decoder_thresholds_v1_1`; parent v1.0 files and locks are preserved. Record parent/config/source hashes before materializing Phase 8 training traces. The amendment changes only finite candidate generation from raw quantiles to their next larger float64 value. No post-test optimization is authorized.

## Score, persistence and action

Score is `(activity[bodyId=10010] + activity[bodyId=10001])/2`: left and right DNp01, confirmed against frozen node identities. No other neuron influences the decision. Save all ten descending-neuron traces as exploratory activity; do not infer direction from them. Labels, roles, coordinates, radii, future frames and stimulus metadata are absent from the decoder API. Evaluator role/split fields are used only outside decoding to select training negatives.

The primary clock is regular float64 millisecond ticks from zero at dt=1 ms. Input state is finite nonnegative float64 `(T,321)` with the exact int64 frozen body-ID vector. Complete Phase 7 saved activity includes initial and endpoint states. Decode only times `< explicit_duration_ms`, excluding the diagnostic endpoint. Shorter prefixes are supported for causality tests but are not complete recorded episodes.

At time k, the causal sustained score is the minimum over indices `[k-20,k]`, eligible only for k>=20. This closed 21-value window represents 20 elapsed intervals. Use `sustained_score >= threshold` and emit one Boolean event impulse at the first eligible crossing. A Boolean request stays latched afterwards, regardless of subsequent activity; no resetting pre-onset events to create later timely events. The decoder does not suppress early alarms by gating the score to the observation window. The window `[0.2,1.0)` s remains available to later evaluators, not the decoder's input or event filter.

An always-silent threshold uses a named sentinel and JSON null, never infinity. The streaming implementation uses a monotone deque, O(T) work and at most 21 history entries. This is an efficiency improvement in software, not a change to the decision rule. Validate it bitwise against an independent brute-force slice reference, equality and drop cases, randomized signals, prefixes and a separate sample-by-sample interface. Runtime measurements are evidence for this implementation only, not a claim that it is faster than every batch method.

Output action: `escape_initiation_requested`, optional first event time, single impulse and latched request. Steering is null with reason `unavailable_no_spatial_mapping`. No jump magnitude, direction, velocity, flight state, actuator, trajectory or escape-success label is generated. The action is an engineered rule applied to modeled activity, not a prediction of a biological fly's movement.

## Candidates and calibration gate

Materialize all 192 training-negative clips (64 families × three matched negatives) from their hash-verified frozen Phase 6 encoded input through the unchanged Phase 7 simulator. Save all DN/score/sustained traces before candidate generation. Each episode contributes its maximum eligible sustained score, including the full episode before onset, excluding the endpoint. Invalid/nonfinite runs fail rather than being omitted.

Derive 31 equally spaced quantiles on those maxima; advance each raw value by `nextafter(value,+inf)` and deduplicate while preserving all quantile indices/levels/raw values. Add the always-silent sentinel; at most 32 candidates. Reject non-training, positive, duplicate, invalid or overflowing records. Also save original raw-quantile candidates as a clearly labeled audit. Tiny positive thresholds separate exact-zero numerical silence; they do not establish noise robustness or neural calibration.

For this phase's demonstration, use the **highest training-negative quantile** candidate, declared before outcomes and labeled `provisional_not_validation_selected`. Replay the existing eight Phase 7 training samples and save requests/plots. No validation or held-out simulation is performed. Do not select a parameter from their success or change timing/dynamics to rescue output.

Final threshold tuning is explicitly pending the Phase 6 handoff gate requiring integrated feature-only and linear temporal controls. Those controls are later-phase work and absent here. Preserve the specified future selection rule: validation timely TPR maximized with full-episode FPR<=0.05, ties lower FPR then higher threshold, silent sentinel always feasible. Only the pure ranking rule is tested on synthetic assessments in Phase 8. No primary calibration or final threshold freeze is claimed; production APIs reject a final-calibrated status and provide an explicit gate error.

## Saved schema and validation

Decoder schema 1.0 NPZ: Unicode scalar schema/decoder versions; float64 `times_ms`, `score`, `sustained_score`, `dn_activity`; int64 `dn_body_ids`; Boolean `eligible`, `escape_event`, `escape_requested`. At 1 s, T=1,000 and DN layout is `(1000,10)`. Ineligible sustained-score entries are zero with `eligible=False`, rather than NaN or a valid score. Action JSON records first event or null, threshold kind/value, provisional status, null steering and abstract semantics. Metadata saves source activity/input/config/model hashes, decoder config/amendment, environment, invocation and output hashes. Existing IDs require explicit overwrite, and outputs stay within Phase 8.

Tests: body-ID/clock/dimension/hash rejection, bilateral averaging, exclusion of other DNs, elapsed persistence, equality, brief pulses, current drops, no early eligibility, one-shot latch, first pre-onset event preservation, prefix/future causality, endpoint exclusion, sentinel, tiny-threshold amendment/original audit, training-only candidate budget and provenance, ranking/ties, calibration gate, real saved Phase 7 replay and saved array round-trip.

Validation records all actual commands, test outcomes, runtime, activation clipping from each pipeline run, candidate provenance, numerical reproducibility and before/after preservation. Decoder tests and requests are engineering evidence only. No H1/H2 result, balanced-accuracy experiment, held-out performance, steering validity or biological fidelity claim follows. Missing Phase 0 evidence and earlier progress PDF remain documented. No commit or push.
