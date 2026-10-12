# Phase 9 engineering validation v1.0

Status **PASS / COMPLETE_ENGINEERING**. UTC 2026-10-11T17:19:13.253305+00:00. Scope: deterministic abstract planar world, bounded delayed escape actuator, relative camera, causal frozen-model coupling and geometry-based metrics. The separate protocol/plan/config and five fixtures were fixed before outcomes. Parent open-loop protocol, encoding normalization, circuit, dynamics and decoder calibration were not tuned.

## Implementation and evidence actually run

The stabilized camera uses pinhole-style circular billboards rendered by the existing Phase 5 rasterizer. World positions change after a decoder request, and therefore change subsequent frames. The first request latches backward/lateral translation, with fixed20 ms delay, acceleration400 and speed cap20 in abstract units. No body yaw, camera rotation or flight biomechanics is implied. Frame prefixes alone enter the frozen encoder; world geometry/danger remain evaluator-only. Strict 60 Hz availability feeds the existing 1 ms Euler step, with scale0.4 applied once. Phase 8 bounded-history streaming initiation and normalized DNp06 steering agree exactly with their batch interfaces.

- **28 Phase 9 tests passed**, zero failures/errors/skips. Tests cover geometry/tangency/tunneling, initial/fractional/horizon collision, boundary failure, delay/latch/bounds, projection, dangerous versus safe geometry, streamed/batch full neural states, decoder/drive equivalence, causal pre-onset prefixes, fractional frame timing, all five seeds, deterministic replay and saved/hash/path guards.
- **382 existing tests and 159 Phase 4 integration assertions passed before and after**, with unchanged counts. Outputs were redirected into Phase 9; earlier-output-writing validators were not run.
- Ran all five primary world fixtures plus both side fixtures for all five synthetic seeds: **15 fixed model runs and 15 exact repeat runs**, no excluded/failing fixture. Saved full world/frame/neural/DN/input/decision traces, configs, actions and per-episode metrics. Every neural run was finite, direct DN input zero, and activation clipping zero. Saved arrays/JSON/hash checks passed. World input differs from original benchmark observations; thresholds were reused, not refitted or claimed calibrated for this domain.
- Ran a scripted action-on/action-off plumbing check: equal frames at300 ms before the command, then 100 differing pixels and 1.09 world-unit position difference at400 ms. This verifies action-to-future-input coupling; it is not a controller baseline or efficacy estimate.
- Executed the environment CLI on the head-on fixture: arrays and metrics equal integrated output. Inspected/recorded plots separately in delivery evidence. Runtime commands and versions are in JSON/logs/XML.
- **2151 frozen execution files unchanged** by before/after SHA-256 inventory. The launcher also verifies the actual repository parents before/after and records the isolated execution snapshot. No dependency installation, commit or push was performed by Phase 9.

## Fixed fixture outcomes

| Fixture/condition | Stationary-fly danger | First request ms | Turn | Escape success | False alarm | Final clearance |
| --- | --- | --- | --- | --- | --- | --- |
| world_head_on_primary | True | 239.0 | 0 | True | False | 12.31 |
| world_left_primary | True | 239.0 | 0 | True | False | 12.31 |
| world_right_primary | True | 239.0 | 0 | True | False | 12.31 |
| world_static_primary | False | None | 0 | None | False | 18 |
| world_near_miss_primary | False | 239.0 | 0 | None | True | 13.16 |
| world_left_spatial_s55010 | True | 239.0 | 0.5725 | True | False | 12.31 |
| world_right_spatial_s55010 | True | 239.0 | -0.8359 | True | False | 12.31 |
| world_left_spatial_s55011 | True | 239.0 | 0.608 | True | False | 12.31 |
| world_right_spatial_s55011 | True | 239.0 | -0.7354 | True | False | 12.31 |
| world_left_spatial_s55012 | True | 239.0 | 0.6198 | True | False | 12.31 |
| world_right_spatial_s55012 | True | 239.0 | -0.7862 | True | False | 12.31 |
| world_left_spatial_s55013 | True | 239.0 | 0.6928 | True | False | 12.31 |
| world_right_spatial_s55013 | True | 239.0 | -0.6633 | True | False | 12.31 |
| world_left_spatial_s55014 | True | 239.0 | 0.7109 | True | False | 12.31 |
| world_right_spatial_s55014 | True | 239.0 | -0.6474 | True | False | 12.31 |

Metrics use geometric stationary-fly contact as danger, not expansion. Success is defined only for dangerous fixtures, requiring timely request, survival through the inclusive1s horizon and final clearance>=1. Harmless episodes have success=None and are not counted as successful escapes. Pre-onset requests, misses, minimum swept clearance, path length, actuation/motion times and failure details are saved per episode. Collision/boundary termination differs from horizon truncation. Physical horizon contact counts as failure; a decoder event at1s remains excluded. No post-terminal decision or future neural state is saved.

## Reproduction and compatibility

Run `MPLCONFIGDIR=/tmp/fly-phase9-mpl ./venv/bin/python -m connectome.scripts.phase9.launch --task validate`. Definition/model/source changes after completion are rejected; numerical traces and outcomes must match saved values. Deterministic reruns are not independent trials. See the Phase 9 README for CLI use and schema1.0.

The user pushed Phase 6 during planning, stashed later phases, updated root README and removed legacy Phase 1 paths. Missing Phase 7/8/planning files were restored from the local stash without popping it. Earlier strict freezes include the original README/legacy paths, so the launcher uses a temporary snapshot with exact verified archival bytes. Current README, branch, stash and Phase 1 cleanup remain intact. `execution_snapshot.json` and workspace preservation inventories distinguish original workspace evidence from frozen execution evidence. Only Phase 9 results are copied back.

## Unresolved scientific issues and boundaries

This is engineering completion of Phase 9, not a behavioral performance experiment. The five fixtures are not a representative held-out distribution; the original benchmark test cohorts were unused. World-domain primary calibration and separate spatial calibration remain unestablished. Synthetic retinotopy, DN motor interpretation, billboard/stabilized-camera/translation-plant assumptions and tiny silence thresholds require later robustness work. Multiple silhouettes and image-edge clipping can invalidate the frozen encoder and remain visible in diagnostics. Finite-horizon survival is not permanent safety. No biological movement calibration, wiring advantage, H1/H2 assessment, shuffled/NN control or Phase 10 implementation occurred. Historical Phase 0 evidence/PDF gaps and earlier specification discrepancies remain preserved.

## Final delivery audit

Two successful full validator invocations passed strict recorded numerical comparisons, in addition to the per-fixture exact reruns. The initial development test failure was a Phase 9 adapter type mismatch; its logs/XML and definition are retained under `development_archive/`, and the source-only repair is documented without world/model/fixture retuning. Final unique suites: **410 tests plus159 integration assertions passed**. All **2,139 current-workspace parent files** and **2,151 frozen execution files** retained before/after hashes in their respective scopes. All Phase 9 source hashes and recorded episode artifact hashes were rechecked, and three plots were visually inspected. See `delivery_verification.json`.

Observed limitations: all13 dangerous fixed fixtures met the predefined finite-horizon escape criteria; the static fixture remained silent, but the expanding harmless near-miss triggered a false alarm. Requests in the approaching fixtures occurred at239 ms and first motion at260 ms. Synthetic encoder frame validity ranged from71.7% to100%, with some trajectories moving objects onto the image edge. Frames and validity are saved; normalization and encoder rules were not changed to hide clipping. Both neutral and synthetic commands succeeded in these simple danger fixtures, so this does not establish a benefit of steering or detailed wiring. This is feedback-coupled sensing with a one-shot latched escape actuator, not an adaptive navigation controller. World-domain calibration, noise robustness and broader behavioral validity remain unresolved.

The numerical methods/design research is recorded with primary-source links in [research notes](../research_notes.md). Earlier document/interface discrepancies remain in the preserved [Phase 7 specification](../../phase7/specification.md); no parent protocol file was silently revised.
