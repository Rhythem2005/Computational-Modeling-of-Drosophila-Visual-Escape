# Phase 11A — proposed training and calibration plan

Status: **AWAITING USER APPROVAL**. Planning only; no implementation, benchmark fitting, calibration run or test evaluation is authorized by this document. Prepared 25 October 2026 after reading the saved Phase 10 configuration, specification, validation and unexecuted job plan.

## Scope and objective

Train the conventional references and calibrate fixed models for the existing open-loop visual-expansion task. Every architecture receives the same frozen per-neuron visual input for its mapping. The task is to distinguish approaching/expanding objects from stationary or sideways-moving objects and determine when to request escape. This is not free navigation, webcam training, biological motor learning or a comparative performance conclusion.

This is the training/calibration part of Phase 11, not all of Phase 11. Held-out evaluation, comparative experiments, ablations, statistical inference and later audits/reporting remain separate work requiring subsequent authorization. Do not mark Phase 11 complete after training alone.

## Models and what is learned

| Architecture | Weight fitting | Decision calibration |
| --- | --- | --- |
| Frozen Circuit v2 | None; preserve measured connectivity and primary dynamics | Preserve verified Phase 8 primary calibration; obtain separate calibration for other gain/mapping conditions |
| Population-average circuit | None; preserve Phase 10 matrix | Own threshold per condition |
| 30 primary weight shuffles | None; preserve all predefined matrices/seeds | Own threshold for each seed/condition; never choose a best shuffle |
| 30 secondary degree rewirings | None; retain all validity/mixing records | Own threshold for each eligible seed/condition; report failures without redraw |
| Feature-only control | None; predeclared fixed rule | Own threshold per representation |
| Linear temporal control | Two nonnegative coefficients, training labels only; fixed zero bias/ridge | Own threshold after fitting |
| Conventional GRU | All 16,241 parameters of the predeclared 321-input, 16-hidden-unit, scalar-output GRU | Own threshold after validation checkpoint/rate selection |

Previously fitted/calibrated Phase 8 artifacts may be reused only after verifying complete identity of inputs, mapping, dynamics, fitting procedure and provenance. Any new condition gets its own separately saved fit/calibration. Never overwrite or silently change earlier frozen values.

## Dataset and leakage boundary

- Use the saved Phase 5.5 benchmark manifest, Phase 5 stimuli and frozen Phase 6 encodings/normalization. No fresh split, extra examples or normalization fitting.
- Training: 64 families, 256 clips. Validation: 32 families, 128 clips. Each family contains looming, two matched static controls and translation. Keep every family in its existing partition.
- Only training labels contribute gradients or linear coefficients. Validation chooses stopping checkpoints, learning rate and decoder threshold using the already declared rules.
- All test-ID and OOD cohorts remain unavailable to training/calibration loaders. No test neural responses, decisions, metric plots or model selection. Hash-only integrity verification is permitted.
- Model forward functions accept input arrays, not labels, scenario types, geometry or future frames. Preserve seconds-to-ms conversion, causal zero-order hold, zero initial state, no warmup and half-open decision timing.

## Fixed GRU training procedure

Use the installed NumPy implementation and ./venv/bin/python; no new dependencies or framework switch. Input dimension 321; hidden size 16; full-episode causal BPTT; episode BCE on maximum causal logit in [200,1000) ms. The decoder consumes sigmoid scores. Use Adam, batch size 16, fixed global gradient clipping at norm 5 and the saved initialization/shuffle conventions.

Run seeds 55100–55109 at both learning rates .0003 and .001. For every seed/rate: at most 200 epochs, early stopping after 20 epochs without improved validation BCE, restore the earliest best validation checkpoint. For each seed retain the better learning rate; an exact tie chooses the smaller rate. Keep ten selected models per mapping, not one model chosen across seeds. Retain both rate histories and any failed trial, without replacement seeds or unregistered retries/settings.

Start with the primary uniform-population mapping, then execute all five predefined synthetic mapping seeds 55010–55014 as separately named secondary conditions. These representations remain engineered assumptions; no best mapping is selected. The full existing plan contains 60 two-rate GRU searches: **120 training trials**, producing up to **60 selected GRUs**. Primary alone is 20 trials and up to ten selected GRUs.

The two rate gain conditions apply to fixed rate matrices, not GRU gate weights. Do not invent additional GRU gain rescaling or equal-parameter claims; the learned baseline has more fitting opportunities than the fixed anatomical circuit.

## Calibration and condition budget

After weight/checkpoint selection, use each model's own training-negative sustained-score quantiles: at most 31 quantiles advanced by the approved next-float rule, plus the silent sentinel. Validation selects maximum timely TPR under full-episode negative FPR <=.05; ties prefer lower FPR then higher threshold. Preserve the closed 20 ms persistence and first-event latch, including early alarms.

The saved full six-mapping plan has 744 fixed rate-model/gain/mapping conditions, 12 feature/linear conditions and 60 selected-GRU conditions: **816 planned calibrated conditions**. These are not 816 gradient-trained networks. All 30 primary weight nulls remain represented; failed required native conditions block a later H2 confirmation, rather than shrinking the ensemble.

Record input/config/manifest/model/source hashes, mapping and training seeds, full candidate assessments, chosen thresholds, diagnostics and declared model status. Bind each selected checkpoint and calibration into a checked freeze before any later test evaluation. Smoke-only or untrained weights cannot qualify.

## Implementation and resource gates after approval

1. Reverify Phase 10 parent hashes, graph bank, dataset isolation and saved environment. Snapshot earlier files and preserve the current untracked Phase 10 work. Use the verified isolated legacy-path execution approach; do not modify frozen parent implementations, results or locks.
2. Add a separate Phase 11 training/calibration runner, reusing Phase 10 GRU/Adam/model/calibration primitives. Add job identities, failure records, incremental output and checkpoint/resume support. A complete resume must preserve optimizer moments, update count, RNG/shuffle state, best checkpoint and patience counter; verify against uninterrupted training. Otherwise restart the same interrupted trial deterministically, explicitly recording the restart.
3. Time a representative batch/epoch at the frozen settings and measure memory/output size before launching the full schedule. This is profiling, not a new hyperparameter search. Report estimates based on measurements; no runtime promise is made now. Pure NumPy CPU training and saving neural traces may be costly. Stream inputs/results and avoid duplicate regeneration. If resources cannot support the predeclared plan, report the limit; do not quietly reduce seeds, epochs, mappings or data.
4. Train primary GRUs and fit/reverify the primary linear control. Calibrate the fixed primary models and selected GRUs, preserving any identical existing Phase 8 artifacts.
5. Execute all planned secondary mapping/gain conditions using the same fixed budgets. Save failures and scale/clipping/stability/runtime diagnostics for every attempted condition. Cache/reuse computation only when complete input/model/condition identity is verified.
6. Run relevant regression and new orchestration tests, verify resumed/reloaded inference and complete condition coverage, check all artifact hashes and before/after preservation, and save a training/calibration validation report. Do not run held-out evaluation or draw rankings/conclusions.

## Deliverables and completion gate

Deliver trained checkpoint sets, both-rate learning histories and selection records, fitted linear coefficients, per-condition calibrated decoders/freezes, an exact job-status/failure ledger, resource measurements, reproducibility configuration, tests and a concise limitations/readiness report. Validation plots are clearly calibration/training evidence, not independent performance results.

Training-stage completion requires every planned job to have a verified result or an explicit failed/blocked status; unresolved required failures mean the stage is not fully ready for confirmatory evaluation. Model/threshold freeze and no held-out use are mandatory. No commit/push, dependency installation, branch cleanup or Phase 12+ work is included.

Await explicit user approval before implementing or running this plan.
