# Phase 11A — partial delivery and blocked resource gate

Status: **INCOMPLETE — BLOCKED AT GATE C**. User authorization: 25 October 2026.
No training/calibration schedule reduction, scientific-rule change or held-out evaluation occurred.

## Gate outcomes

| Gate | Actual result |
| --- | --- |
| A — Integrity | PASS: 17 Phase 10 source hashes, 343 delivered artifact hashes, 62 graph identities / 124 gain conditions verified; 256 training and 128 validation clips; 640 test identities rejected before file access. |
| B — Engineering | PASS: 525 tests, 0 failures/errors/skips; 18.790 seconds for the final combined suite. |
| C — Resources | BLOCKED_RESOURCES: reported discharging battery capacity is below the measured full-schedule estimate. |
| D — Primary | NOT EXECUTED. |
| E — Secondary | NOT EXECUTED. |
| F — Freeze | NOT EXECUTED. No scientific model freeze exists. |

## Implementation and verification

Isolated orchestration lives in `connectome/scripts/phase11/`. It reuses the
unchanged Phase 10 GRU, full BPTT episode-BCE, Adam, model scoring and threshold
calibration, and the verified historical namespace reconstruction. New I/O stays
inside Phase 11. The original training-plan document remains unchanged; the newer
README records the user's authorization and execution commands.

The final 525-case suite contains 499 existing tests and 26 Phase 11 tests. An
initial 516-case development suite also passed before the remaining nine cases
were added; this is repeated engineering verification, not independent experiments.
Tests cover resumed/uninterrupted equality to the frozen trainer at four batch/epoch
interruptions, Adam/RNG/order/patience/best-weight restoration, checkpoint tampering,
uncommitted generations, atomic publication, six mapping caches, held-out guards,
936 unique schedule IDs, FPR/sentinel feasibility, early/missed/boundary decisions,
subnormal JSON/reload/comparison/inference and rejection of smoke/untrained freezes.
The separate historical 159-assertion simulator program was not rerun in this stage.
Full production end-to-end training, calibration and freeze paths remain unexecuted.

`engineering/*/tests.log`, `tests.xml` and `summary.json` retain both invocations;
`gate_B.json` binds the final passing suite to 13 source/document hashes. Exact
commands, legacy-copy paths and exit codes are in `execution_*.json`. Gate A records
the actual Python/NumPy/YAML/platform and full frozen configuration. No new dependency
was installed. Final Git state remains main tracking origin/main, with Phase 10 and
Phase 11 work untracked; no commits or pushes were made.

## Actual experiment and job counts

| Category | Completed |
| --- | ---: |
| Registered GRU training trials | 0 / 120 |
| Selected GRUs | 0 / up to 60 |
| Calibration conditions | 0 / 816 |
| Linear fits | 0 |
| Scientific freezes | 0 |
| Held-out inference/evaluation | 0 |
| Resource-profiling epochs | 1 |

The profiling epoch used all 256 training clips in 16 batches, with 16 Adam updates,
and all 128 validation clips in eight forward batches. Its weights are explicitly
profile-only, stored under `resources/`; they are not a completed registered trial,
selected checkpoint, calibration or scientific freeze. `job_ledger.json` retains
all 936 registered identities, each marked BLOCKED_GATE_C, without replacement seeds.

## Measured resources

- Input-cache preparation: 0.929 seconds for all 384 allowed uniform clips.
- One full frozen-setting epoch including checkpoint writes and validation: 1.679 seconds.
- One reference circuit clip: 0.014891 seconds.
- Peak resident memory: 327.6 MiB; installed RAM: 16 GiB.
- Compressed representative rate output: 66,659 bytes; GRU parameters: 126,724 bytes.
- Estimated full training: 1.18–11.19 hours, from frozen earliest-stop 21 / maximum 200 epochs and all 120 trials.
- Estimated fixed rate inference: 1.18 hours for all 744 × 384 clips.
- Combined estimate: 2.36–12.37 hours **before spatial preparation, calibration candidate decoding and other overhead**. This single-epoch/clip extrapolation is provisional, not a runtime guarantee.
- Conservative disk allowance: 59.52 GiB including output duplication and 5 GiB reserve; measured available disk: 59.97 GiB. This passes narrowly and must be rechecked before execution.
- Phase 11 artifact bytes before this report: 2,947,904; full workload artifacts have not been generated.

The captured `pmset -g batt` reports AC Power **and** 19% discharging with 1:32
remaining. These contradictory source labels do not demonstrate sustained power.
The reported 92-minute discharge horizon is below even the 2.36-hour lower estimate.
The resource gate therefore stopped before registered fitting. Reliable sustained
power and a fresh resource check are required to advance. Checkpoint/resume reduces
lost work but does not establish full-schedule resource feasibility.

`gate_C.json` contains all batch/write timings, memory, storage, raw power evidence,
thread settings and estimate assumptions. `hardware.json` records the approved
read-only memory query. Profiling BCE is a profiling/calibration measurement only;
there was no checkpoint, rate or threshold selection and no generalization result.

## Preservation and limitations

The independent final audit rehashed **2673 earlier files unchanged**, all 13 tested
Phase 11 sources/documents, all 384 cached uniform frame drives, and the final
profiling checkpoint/model arrays. All cached inputs have 100% valid frames;
per-clip encoder channel-cap fractions range from 0 to 0.225. This input saturation
is distinct from neural activation clipping; the single profiled rate clip is not
a benchmark-wide clipping assessment. Five spatial seeds passed engineering cache
checks on the previously used training fixture, but complete spatial coverage and
failures remain unmeasured until Gate E. Nothing was excluded by outcome.

The `5e-324` round-trip, exact-equality trigger and silence comparison pass here;
`numerical_verification.json` records the smallest float's bit pattern. It provides
only a one-ULP margin above silence, no established noise robustness or portability
to environments that flush subnormals. Candidate feasibility, sentinel-only
selection, early alarms and misses are independently diagnosed by the implementation;
no real per-condition calibration assessment exists yet. Validation is reused only
under the frozen checkpoint/rate/threshold rules and will be labeled calibration
rather than independent generalization. The learned GRU has 16,241 fitted parameters,
whereas anatomical/control rate weights remain fixed. No wiring-advantage,
biological-fidelity or general escape-performance conclusion is supported.

Phase 11A does **not** satisfy its completion gates. Gates D–F, all registered
training/calibration jobs, complete spatial diagnostics, and final model/threshold
freezing remain outstanding. No work continues in the background.
