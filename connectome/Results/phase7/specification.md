# Phase 7 integration contract 1.0.0

Scope: Phase 5 schema-1.0 movies → frozen Phase 6 encoder 1.0.0 → existing Phase 4 rate simulator on frozen Circuit v2. This phase records neural activity only. No action decoder, thresholds, behavior, steering or competing architectures are implemented.

## Frozen inputs and initialization

The constructor verifies the Phase 5.5 protocol lock, Phase 6 source/protected-file lock, semantic config/normalization/mapping/manifest/integrity hashes, training-only normalization provenance, and hashes of all 1,024 encoded artifacts. Nothing is regenerated in an earlier phase. Normalization scales remain 8.632185525889524 and 8.417362938348457. No fitting or parameter search occurs.

The Phase 4 loader validates 321 neurons, 11,557 edges, 91,023 synapses, body IDs, types and sides. The adapter requires exact int64 node CSV ordering; reordered or duplicate IDs fail rather than silently remap. Drive is float64 `(T,321)`, channels float64 `(T,2)`, timestamps float64 `(T,)` in seconds. The adapter verifies exact uniform broadcast to LC4/LPLC2, zero direct drive to all ten DNs, nonnegative finite bounded values and frozen encoder hashes. W remains `[post,pre]`, counts divided by 172 with the existing assumed sign map.

Every episode starts with zero state, zero bias, no noise and no warmup. The pipeline loads the unchanged Phase 4 config. Only episode duration changes: the existing 500 ms default becomes the explicitly declared stimulus duration (1,000 ms for benchmark movies). Gain 0.5, tau 10 ms, dt 1 ms, input_scale 0.4 and clip_max 50 remain unchanged. Duration must be positive, finite and an integer number of Euler steps; all frames must occur strictly before the explicit episode end. A bare encoded series does not determine duration. Holding a last frame beyond its timestamp is deliberate, not an inferred extra frame.

## Units and causal timing

Encoder features use pixels and seconds; normalized drive and activity have arbitrary model units, never spikes/s. The adapter converts each simulator query from ms to seconds by division by 1,000, then selects the latest frame timestamp `<= query_s` using strict floating-point comparison. There is no early epsilon tolerance or interpolation. Before the first frame the input is zero; after the final frame its drive is held until the explicit episode end. A frame between Euler grid points is first used at the next eligible step start. At 60 Hz, frame 1 at 16.666… ms is first used at 17 ms. Numerical resolution does not add sensory information.

Phase 4 applies scale 0.4 exactly once inside `run_simulation`. At `t[k]`, Euler reads unscaled frame drive and computes `x[k+1]` using the scaled input and `x[k]`. Consequently `x[k]` precedes the input update at `t[k]`. State arrays include initial and endpoint samples (1,001 for a 1 s episode); callback inputs have only 1,000 step-start samples. The 1,000 ms endpoint state is saved for diagnostics and is outside the later `[0.2,1.0)` decision window. No decision is calculated here.

Generator parameters and evaluator labels stay outside encoder computation. Schema metadata supplies only the explicit episode end to scheduling; its identity and hashes are attached to provenance after encoding. The public `run_frames` interface accepts exactly frames, timestamps and duration. The stable Phase 5 loader performs schema validation before `run_saved` encoding; legacy versionless stimuli are rejected by Phase 7.

## Validation design

Before sample activity inspection, eight fixed IDs in `pipeline_config.yaml` select all four matched roles from `train_f0000` and `train_f0001`. No held-out neural simulation or fitting is needed for this integration gate. Earlier Phase 6 held-out encoded artifacts are checked for file integrity only. Every sample passes through Phase 5 generation, Phase 5 saved schema/loader, frozen encoder and Phase 4 simulation, then is compared bitwise with replay of its frozen Phase 6 encoding. A second identical run checks state reset and deterministic activity.

Required checks: all earlier tests pass before/after; earlier files retain identical content hashes; exact mapping and dimensions; strict availability at fractional/irregular/delayed and 60 Hz timestamps; explicit units; single application of scale; independently computed Euler trajectories and update/readout timing; metadata exclusion; future-frame prefix invariance; zero contrast; silent static/terminal/translation controls; finite nonnegative looming activity; no clipped activation in samples; saved array round-trip and reproducibility.

Report activation clipping by recomputing preclip activation `gain * W_signed @ x[k] + bias + input_scale * u[k]` at every step and counting values above clip_max. Encoder cap fraction is a separate measure. Store both, plus runtime and peak activity. These are numerical integration diagnostics, not hypothesis H1/H2 or biological findings. Timing and scale are fixed before sample runs; a failed gate is reported without retuning.

## Output schema 1.0

NPZ uses `allow_pickle=False` and stores a Unicode scalar `schema_version`, int64 body IDs, float64 `times_ms`/`states`, `frame_timestamps_s`/`channels`/`frame_drive`, `step_times_ms`, int64 `step_frame_indices` (-1 before first frame), `step_drive_unscaled`, and `step_input_scaled`. State layout is `(steps+1,321)`; step drive is `(steps,321)`; frame drive is `(frames,321)`. No input is sampled at the endpoint. Config JSON contains the resolved Phase 4 config; metadata JSON contains units, initialization, lock/model/config/input hashes, metrics, environment and invocation. Phase 5 sample files preserve complete stimulus configs. Existing output IDs need explicit overwrite, and the activity saver confines output to Phase 7. File sets are not transactional; incomplete files must not be treated as a completed run.

## Existing discrepancies and unresolved evidence

- Root README describes archival Circuit v1 as the completed circuit and gives obsolete hemisphere counts. Active v2 CSV/JSON, Phase 4 loader and Phase 6 mapping agree on v2 and its asymmetric counts. Earlier README is preserved.
- Phase 3 handoff describes divisor 172 as an intra-LPLC2 maximum. Actual CSV and the Phase 4 named-edge check identify LC4 body 81112 → DNp04 body 531898 with weight 172. Divisor and matrix are unchanged.
- Phase 3 documents describe neurotransmitter confidence as 0.84–0.99; DNp01 CSV values are approximately 0.50–0.56, already recorded in Phase 6. Positive functional signs remain an explicit modeling assumption.
- Phase 4 specification describes dictionary input while its actual high-level interface accepts `u_func(t_ms,n)`. Existing input constructors translate dictionaries to that callback; Phase 7 uses the actual callback interface without changing the simulator.
- There is no separate Phase 0 completion artifact in this checkout. Environment availability and working earlier implementations can be verified, but historical Phase 0 completion cannot be independently certified.
- `output/pdf/FLY_Project_Progress_Through_Phase_6.pdf` is absent in this checkout. It was not reviewed or recreated.

No physiological calibration, receptive fields, general-scene encoder, behavior, efficacy comparison or biological fidelity is established. Sample scope is eight training clips and synthetic timing/causality fixtures, not the full neural benchmark. Remaining roadmap phases and optional webcam/3D demonstrations require separate authorization.
