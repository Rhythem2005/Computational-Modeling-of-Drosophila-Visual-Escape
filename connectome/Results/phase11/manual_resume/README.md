# Continuous CPU execution and manual pause/resume — verified preparation

**Final status: BLOCKED by current power conditions. No production training ran.**

## Thermal feature removal

The pre-session `launch.py` backup was verified against the SHA-256 recorded in the
session implementation's before inventory (`263c9d1755cbeac0dc49191a6bb12f52b36861d0d0b008a57616ff4042f81160`).
The active launcher matched the session artifact index. Its actual diff was saved
as `thermal_launch.diff`, and the pre-session bytes were restored before the manual
interruption corrections were applied.

The six exclusively thermal feature files were hash-verified, removed from active
locations and retained as text under `historical_thermal/source/`:
`worker_guard.py`, `session_telemetry.py`, `sessions.py`, `session_worker.py`,
`session_launch.py`, and `tests/test_sessions.py`. Their evidence directory and stale
feature lock were archived, with a HISTORICAL marker. No active session readiness,
automatic cooling, work-session policy or two-trial cap remains. Archived indexes
refer to former locations and are historical, not current readiness evidence.

## Original-code audit and necessary corrections

| Capability | Original finding | Current result |
| --- | --- | --- |
| Float64 full BPTT, Adam, RNG/order, cursor, patience/best state | Already checkpointed and restorable | Preserved; no checkpoint schema change |
| Per-batch/epoch atomic state publication | Present inside execution copy | Preserved |
| Ctrl+C to launcher | Could exit without waiting/finally publishing child's newest state | Signal becomes a request; worker pauses after a committed boundary; parent waits and publishes before exit |
| Restart after process/laptop exit | Restored the last canonical published generation | Same mechanism, now with verified final publication on graceful stop |
| Completed trial recognition | Could reset COMPLETE to RUNNING and re-register | Verified completed reports/checkpoints reused; completion registered once |
| Report committed before ledger registration | Could finalize through trainer unnecessarily | Verified report recovered directly and registered once |
| Completion during periodic publication | Could expose a report/ledger after copying an older pointer | Final pointer/selected arrays refreshed before completion report and ledger |
| Whole ordered Phase 11A CLI | Separate primary/secondary/freeze invocations | `--task continuous` runs those existing gates in order, reusing completed phases |
| Resource gate | Disk, peak RSS and battery-runtime check only | Adds current stable AC, reclaimable-memory estimate, process exclusion and OS pressure checks |

The existing training equations, initialization, Adam updates, batch size 16,
float64 precision, partitions, mappings, learning rates/seeds, clipping, stopping,
calibration and model-selection rules are unchanged. `training.py` gained only calls
to the manual-stop boundary after existing checkpoint commits. `dataset.py` checks
for a stop between input-cache records. No delay or training-budget cap was added.

The new `manual_stop.py` signal handler sets a flag. Actual stopping occurs at the
next committed checkpoint or job/score-cache boundary, using a BaseException that
is not classified as a failed scientific trial. The launcher forwards one request
to its child after the child installs handlers, waits, performs final publication,
and prints confirmation. A worker whose parent unexpectedly disappears stops at
its next committed boundary rather than continuing unattended.

A continuous-worker lock and read-only resource checks live in `runtime.py`. They
are runtime safety mechanisms, not a session controller. The original GRU/Adam
implementation and the checkpoint fields/formats are unchanged. Source hashes bind
current checkpoints; changing code after pausing would require review rather than
silently accepting an incompatible resume.

## Verification actually executed

**Gate B: PASS, 542 tests, zero failures/errors/skips**, including the existing 525
cases and 17 new manual-resume cases. The final suite took 31.324 seconds.
Intermediate 538/539/540/541-case suites also passed during incremental engineering;
these are repeated verification, not independent experiments.

Synthetic fixtures use the unchanged 321-input/16-hidden float64 model, batch size
16, both declared rates, 24 time steps and three fixture epochs; a separate fixture
forces the unchanged patience rule to stop at epoch 21 and select epoch 1. They do
not load registered benchmark inputs or execute full registered trials.

Real SIGINTs, process exit and a fresh Python process were tested at:

- a committed minibatch;
- an epoch commit;
- completion of the trial report before ledger registration;
- the boundary between trial identities;
- an epoch boundary followed by early stopping.

Tests required exact equality of final and best weights, all current parameters,
Adam first/second moments and update count, losses/history, RNG state, shuffled
order, epoch/minibatch cursor, patience and best-epoch choice. Wall-clock accounting
and generation-file container hashes were not used as scientific equality criteria.
Exactly two synthetic trial identities completed, each registered once; completed
trials were not trained again. A real parent/child launcher test additionally
verified one Ctrl+C, child exit, canonical checkpoint publication, and a new parent
and child resuming the same committed minibatch. Another test covers completion
racing with publication. Orphan stopping, gate failures and ordered primary →
secondary → freeze progression/reuse were tested with controlled stubs.

Frozen-artifact integrity verification passed again: the historical namespace copy
checked 2,295 parent files; Phase 10's delivered hashes and source/model identities
passed Gate A. Source manifests and exact commands/logs/XML are retained in the
normal Phase 11 results. This report does not claim production end-to-end outcomes.

## Refreshed Gate C — blocked

The final current-source resource profile ran **one profiling epoch**, 16 gradient
updates over 256 training clips plus eight validation batches over 128 clips. An
earlier profile in this task also ran; **two profiling epochs total, zero registered
training trials, zero calibrated conditions, zero held-out inference**. Profiling
weights cannot qualify as selected scientific models. Each profile was saved in a
new timestamped directory under `results/resources/profiles/`, preserving all
historical checkpoint bytes and the job ledger.

Latest measured epoch: **1.705 seconds**, peak process RSS **327.9 MiB**. Live checks
found about **6.55 GiB reclaimable memory**, **59.69 GiB free disk** against a 59.52 GiB
conservative allowance, **no other Phase 11 worker**, and **nominal OS thermal
pressure**. No temperature in degrees C was exposed or inferred.

The machine reported **Battery Power, 64%, discharging**. Gate C is therefore
**BLOCKED_RESOURCES**, with STABLE_AC_NOT_VERIFIED and BATTERY_DISCHARGING. Historical
failures were not treated as passes. Production also performs a fresh preflight,
so an old Gate C PASS cannot bypass current resource failures. Thermal telemetry is
optional where unavailable; unavailable memory/process telemetry fails closed.

Four exact, verified disposable execution copies created in this task were removed
with approval, recovering about 524 MiB; repository data, canonical checkpoints,
logs and the final verification copy were retained. This resolved the initial disk
shortfall, not the power failure. Details are in `temporary_copy_cleanup.json`.

## Actual commands

From `/Users/rhythemsabharwalgmail.com/Desktop/FLY`, **after current gates pass and
after explicit user authorization**, START:

```bash
./venv/bin/python -B -m connectome.scripts.phase11.launch --task continuous
```

PAUSE: press **Ctrl+C once** in that foreground terminal. Wait for:

```text
PAUSED: latest committed checkpoints published to Phase 11 results.
```

A graceful pause exits with status 130. Do not shut down until that confirmation.
`results/execution_continuous.json` records `exit_code: 130` and
`final_publication_completed: true`. The active trial's canonical checkpoint is
`results/training/<job_id>/current.json`, referencing the NPZ generation and SHA-256.
It records epoch, minibatch offset, Adam update count, RNG/order and best/stopping
state. Resume validates pointer/payload/model/source/input hashes before use. If
paused before the first trial starts, no neural checkpoint is expected yet.

RESUME, even after restarting the laptop:

```bash
./venv/bin/python -B -m connectome.scripts.phase11.launch --task continuous
```

There is no invented `--resume` flag. The same command reconstructs the verified
namespace from canonical repository files, restores incomplete trials and reuses
verified completed results. Primary completion precedes secondary work; threshold
calibration and final freeze remain their existing subsequent gates. No held-out
evaluation is part of this command.

A normal Ctrl+C waits for the current update/commit and then publishes it; committed
progress is preserved. An update interrupted **before** commit is not promised to
be recoverable. SIGKILL, power loss, filesystem failure or hard shutdown can lose
work since the last successful canonical publication (nominal interval 30 seconds),
plus in-flight uncommitted work. This is not a hard time bound if I/O stalls. Resume
uses the latest hash-valid canonical commit; temporary execution copies are not
required after a confirmed graceful pause.

To refresh resource evidence after connecting stable AC power, the supported
preparation command is `./venv/bin/python -B -m connectome.scripts.phase11.launch
--task profile`; the shell command should be entered on one line. It profiles only,
not registered trials. `--task preflight` performs live checks without model work.
Current resource telemetry requires normal process/memory-query access; Gate C here
was run using approved execution outside the sandbox.

**Continuous CPU training is not ready to begin while Gate C is blocked.** No
production command has been run, no automatic background execution remains, and
no dependency installation, scientific configuration change, commit or push occurred.
