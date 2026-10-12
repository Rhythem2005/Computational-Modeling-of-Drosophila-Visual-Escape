# Phase 6 handoff

## Required implementation

1. Consume Phase 5 schema 1.0 through its existing loader, then expose only frames `(T,H,W)` uint8 and timestamps `(T,)` float64 to the encoder. Keep evaluator metadata separate by interface design; never send the loader's config/metadata dictionary into encoder feature computation.
2. Begin with causal global LC4-like expansion-speed and LPLC2-like expansion-selective size channels. Select their explicit equations and training-only normalization using the training manifest, then record an encoder version and config before evaluation.
3. Broadcast each channel uniformly to the corresponding Circuit v2 population using verified body IDs; descending cells receive no direct visual input. Mapping to inputs is representation, not biological retinotopy.
4. Output finite, non-negative time-varying drive arrays with an explicit layout, body-ID vector and seconds timebase. Avoid claiming absolute spikes/s. Define interpolation as causal zero-order hold; Phase 7 converts seconds to the simulator's ms timebase.
5. Test zero contrast, static initial/final-size controls, matched translation, both contrast polarities, known onset, fractional timestamps, clipping and fixed-config reproducibility. Report unanticipated responses rather than changing test labels. Contraction/flicker tests need new fixtures; they are pending, not already delivered by Phase 5.
6. Check that perturbing evaluator label/type/radius/speed metadata leaves encoded output unchanged, that altering future frames never changes earlier outputs, and that frame-versus-ms conversions preserve causal availability.
7. Provide plots of each engineered signal alongside stimulus time and independent geometric checks. State which expected responses follow from engineered equations and which are experimentally supported qualitative comparisons.

## Scientific gates

- A static object with the final looming radius must not appear to be a loom solely because of size. Report the encoder's negative-control separation before tuning the network.
- Primary initiation experiments use uniform inputs. A steering implementation is deferred until its location-to-neuron mapping is independently documented. Synthetic mappings must be independent of DN connectivity and downstream outcomes and use the five predeclared seeds.
- Freeze one primary encoder configuration before circuit/baseline comparisons; all architectures receive the same encoded vectors. Feature-only and linear controls must be integrated before tuning the final decoder.
- Verify train/validation/test family isolation and actual frame-content hashes when materializing datasets. Reject duplicate movies across partitions even if their parameter fingerprints differ.
- The primary model remains the existing Phase 4 implementation and defaults. Any alternative dynamics, recurrent ablation, gain rescaling or circuit extension is a separate named condition.

## Completion evidence required later

Encoder implementation and tests, saved training-derived normalization, input schema, version/config hash, causal and metadata-leakage tests, negative-control plots and explicit limitations. A passing Phase 5.5 protocol check is not evidence that the encoder exists or works.
