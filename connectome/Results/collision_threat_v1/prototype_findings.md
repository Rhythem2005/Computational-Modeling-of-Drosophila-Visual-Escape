# Findings from the approved exact-rule prototype

## Outcome

The standalone closest-approach rule met the predeclared five-fixture target. It requested at 237 ms on each dangerous case, survived the one-second horizon with required clearance, and remained silent on static and harmless near-miss. The original circuit requested at 239 ms on each danger and the near-miss. The original feature-only control and new expansion-only ablation requested at 237 ms on each danger and the near-miss. This supports further work on image motion rather than completing the original GRU training as the immediate remedy.

The hybrid preserved all three dangerous escapes at 239 ms. On the near-miss, it retained the circuit's 239 ms pending initiation, correctly withheld physical action while the point-observer model estimated a clear path, then issued an unknown-perception fallback at 767 ms. The observation at 766.666… ms became available at 767 ms and its foreground touched the image border; this was an image-validity failure, not evidence of collision. The gate delay was 528 ms. Its fallback caused a false alarm under the approved endpoint. The rule was not retuned and the pending request was not erased after that outcome.

## What this resolves

- The available camera images contain useful motion information before the old request time. The primary two-channel encoder does not explicitly retain that information.
- The synthetic known-case failure does not require additional GRU training to produce a working engineering counterexample: a fixed image-only rule avoided the three known dangers without either harmless escape.
- Expansion-only triggering remains insufficient on the known near-miss, even with the new feature implementation. Its matched ablation makes that limitation visible.
- The circuit hybrid's current unknown fallback can turn a withheld request into a late false alarm. This is a policy tradeoff rather than a hidden numerical or loading failure.

## What remains unresolved

The point-observer estimate ignores the finite radius of the fly. An object can miss a point while hitting the actual fly; the canceled unknown object scale does not recover a physical safety margin. No safe margin, alternative gate lifetime, canceled pending request, uncertainty threshold or fallback adjustment was fitted or tested. Changing one would be a new policy condition, requiring its own exact specification and authorization.

The rule assumes a rigid circular billboard, constant unknown object radius and locally constant relative velocity. Area quantization and unsupported/clipped observations limit it. Once action begins, acceleration changes relative velocity, but the motor command remains latched. Multiple targets, arbitrary 3-D paths, acceleration, disturbances and biological sensing are not validated. A constant-bearing or point-proximity proxy is not a universal collision detector.

Five previously inspected geometries cannot establish representative reliability, noise robustness or a wiring advantage. The new pipeline receives additional image-derived information; it is not a comparison of neural architectures with identical input representations. The hybrid must be named as such and does not train or modify the anatomical circuit.

## Evidence and safeguards

The [run report](prototype/1793093607177149000/README.md) includes all six controllers individually. Its 73 checks include all 30 preserved adapter checks, all 23 feature checks and 20 rule/gate checks. There were 60 attempts in total, including all 30 exact repeats. The global ledger prevents an extra automatic run. The separate [saved-file audit](prototype/1793093607177149000/saved_file_audit.json) independently rechecked 60 episode hashes/physical outcomes, all 30 repeats, all 30 legacy-reference episodes and internal versus physical request timing. Sensory-invalid episodes and fallback events were retained in the main outcome counts.

Original files, the partial Phase 11 checkpoint and all Stage A evidence remained unchanged. No dependencies were installed, no commits/pushes occurred, and no calibration, training or held-out evaluation was performed. The full GRU schedule remains incomplete and paused.

## Next decision

Prepare a separately bounded follow-up specification addressing finite-body threat estimation and how to handle an old pending request when perception later becomes unknown. State the additional assumptions and safety/false-alarm tradeoff before testing either change. Then define independent behavioral families and their calibration/evaluation separation before authorizing broader evidence collection. Do not consume new scenarios or resume the 120-trial schedule automatically.

Schema note: `controller_states` stores only the recurrent neural state when one exists. The prototype's `stateless` core label for the rules means there is no neural-state vector; causal perception/adjacent-measurement history, decoder persistence and physical latch are stored in their separate measurement/estimate/decision arrays and are not absent from the implementation.
