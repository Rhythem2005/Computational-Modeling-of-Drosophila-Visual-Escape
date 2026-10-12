# Phase 6 encoder 1.0.0 — predeclared engineering design

This document and `encoder_config.yaml` are recorded before any encoder-response inspection. They implement the Phase 5.5 primary uniform-population representation, not receptive fields or biological spike rates. No circuit is simulated here except the explicitly required existing Phase 4 regression tests.

## Design, fitting budget and freeze

Algorithm parameters are fixed engineering choices: minimum absolute contrast 4 uint8 levels, growth window 0.1 s, strict area growth >12 pixels, strict relative radius growth >0.02, output cap 1.0. There are **zero parameter-search trials** and no validation-selected parameters. The sole fit is two 99.5th-percentile scales of strictly positive raw channel values from all 256 training clips (labels are not used). One training pass; no validation or test normalization. Empty/nonpositive scale fails rather than substituting test data.

Generate/hash all movies for integrity, one at a time, and check family isolation and actual frame-content collisions across all cohorts before the freeze. No test features are computed at that stage. Then fit training scales, save normalization with training hashes, and save a source/config/normalization/mapping/manifest freeze lock before computing validation or test responses. All test response inspection is explicitly **post-freeze**. Fixing implementation bugs may require a new lock; changing equations or thresholds after test inspection requires a fresh evaluation protocol, never silent retuning.

## Equations (engineered expectations)

For frame k, let b be its modal uint8 intensity (ties: lowest intensity). Foreground mask M comprises pixels with |I-b|>=4. A=sum(M), equivalent radius r=sqrt(A/pi), contrast c=mean(|I-b| over M)/255. Validity requires nonempty foreground, modal background occupying >50% of the image, and no foreground on any border. Scenes are assumed to contain one solid circle on a uniform background. Noncircular/multiple objects can produce misleading responses; this is not a general computer-vision model.

Choose j as the most recent timestamp <=t[k]-0.1 s, with a 1e-12 s equality tolerance for floating-point arithmetic. Until j exists, both channels are zero. Require every frame from j through k to be valid. Define g=1 if A[k]-A[j]>12 AND (r[k]-r[j])/r[j]>0.02, otherwise 0. Raw channels are:

`LC4_like[k] = g * c[k] * max(r[k]-r[j],0)/(t[k]-t[j])`

`LPLC2_like[k] = g * c[k] * r[k]`

Thus a final-size static circle has zero drive, translation should not activate above the gates despite raster-area noise, contraction is suppressed, and contrast polarity is symmetric. These expectations follow from the equations. LC4 velocity and LPLC2 size/selectivity are literature-supported *qualitative motivations*, not calibrated neural response predictions: Ache et al. (2019) and Klapoetke et al. (2017), as linked in the frozen evidence register. The area/growth gates are a synthetic approximation, not radial-motion-opponency circuitry or optical flow.

Divide each raw channel by its saved training scale and clip to [0,1]. First frame is always zero; the initial static object is not interpreted as an appearance event. Invalid/clipped frames suppress drive, and a full valid window is required on re-entry. Disappearance, background changes, multiple objects, luminance flicker and viewpoint changes are not biologically validated. Pixel scale and frame rate affect raster noise; fixed thresholds target the recorded benchmark.

## Numeric gates, declared before results

These gates assess encoder software and engineered separation only, not Phase 5.5 H1/H2 or behavior. Apply to train, validation and separately post-freeze test cohorts unless a cohort has no member of a named subgroup (record not applicable, not pass).

| Gate | Numeric pass threshold |
| --- | --- |
| Finite/bounded output | 100% of drive samples finite and in [0,1]; all 10 DN columns exactly zero; per-population broadcast difference exactly zero |
| Dataset integrity | 0 duplicate full movies; 0 families crossing cohorts/splits; 1,024 records and 256 families |
| Zero contrast | Maximum absolute drive exactly 0 |
| Static initial / static terminal / translation | Every negative clip has peak of either channel <=0.01 |
| Loom response, each channel | >=95% of looming clips have peak >0.01; for low-contrast OOD use >0.005 and >=90% |
| Polarity | Synthetic matched positive/negative contrast pair: maximum difference exactly 0; each benchmark polarity separately meets loom/negative gates |
| Onset | 0 pre-onset nonzero samples; >=95% of looms begin nonzero within 0.18 s after 0.2 s onset |
| Geometry | Valid unclipped equivalent-radius absolute error <=1 pixel for >=95% of frames; median relative raw-speed error <=0.20 and 95th percentile <=0.50 on active gated frames against independent analytic backward secants |
| Clipping | Border-touching/offscreen/full-field synthetic fixtures have maximum drive exactly 0, no nonfinite value; diagnostics flag invalid frames |
| Fixed-input reproducibility / metadata leakage / future causality | Maximum difference exactly 0; modified suffix leaves prefix output bitwise equal |
| Fractional timestamps / causal availability | Valid fractional timestamps accepted; ZOH uses index of latest frame timestamp <= query exactly, no look-ahead; queries in seconds and milliseconds converted to seconds agree exactly on declared fixtures |
| Test suite | 0 failed tests |

Gate outcomes are recorded even on failure. Do not change labels, cohorts, protocol or cutoffs to pass. Response timing is frame-level; 0.1 s feature history intentionally delays activation and does not claim fly latency.

## Schema and mapping

`CausalEncoder.encode(frames, timestamps_s)` accepts exactly two arrays: uint8 THW and float64 T, nonempty finite nonnegative strictly increasing seconds (one frame allowed). Config, saved normalization and Circuit v2 mapping are constructor state, never evaluator metadata. Return channel float64 `(T,2)` ordered `[LC4_like,LPLC2_like]`, drive float64 `(T,321)`, body_ids int64 `(321,)`, timestamps_s float64 `(T,)`, and diagnostics (area, radius, contrast, validity, anchor index, raw channels). Explicit version/config/normalization hashes accompany output. Unsupported metadata keyword arguments are rejected.

Node ordering is the exact Circuit v2 node CSV row order, matching the existing Phase 4 loader, not numerical body-ID sort. Verify against Circuit v2 JSON as an independent saved artifact, check type/side counts, and assign only `type=LC4,population=visual_input` to channel 0 and `type=LPLC2,population=visual_input` to channel 1. Every other node has channel=-1 and zero drive, listed in `mapping.json`. No neuron has an inferred spatial field.

`causal_hold(values,timestamps_s,query_s)` is an array timing helper, not a simulator adapter: latest available frame, zero before first timestamp, last frame held after the final timestamp. Consumer must specify the episode end; holding alone does not infer duration. Milliseconds are accepted only after explicit division by 1000 outside the encoder. No future-frame interpolation.

## Frozen-context conflicts and scope

Circuit v2 specification/audit describe neurotransmitter prediction confidence about 0.84–0.99; the actual node CSV includes DNp01 confidences around 0.50–0.56. This is reported, not repaired. Encoder uses type/population/body IDs, not these scores. Phase 4 pytest cases and 159 integration assertions are different test granularities and must be reported separately. Phase 5.5 describes clipping/contraction/flicker fixtures as pending; Phase 6 introduces its own clipping (and optional contraction sanity) fixtures without altering benchmark/protocol files.

Unresolved: calibrated responses, actual receptive fields, synthetic spatial mappings, steering, general images/multiple objects, flicker validation, downstream integration/decoding and behavioral evidence. No new dependency, commit or push.
