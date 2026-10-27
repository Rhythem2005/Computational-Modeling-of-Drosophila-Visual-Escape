# Opt-in thermal-aware CPU sessions — preparation v1

**Engineering verified; production not started.** The user authorized preparation
and synthetic/mock validation on 25 October 2026. Explicit future authorization is
still required before running registered trials.

## Behavior

The new `session_launch` entry point dispatches at most **two complete GRU trial
identities** per session, serially, using the existing `train_trial` unchanged.
Training batch size stays **16**, float64 and all scientific settings remain frozen.
The next session waits **180 seconds**. Cooling occurs outside the trial process;
there is no scheduled delay inside an epoch or optimizer step. The default bounded
execution request is one session. There is no automatic unbounded/full-schedule mode.

The existing deterministic order is preserved: primary uniform mapping, seeds
55100–55109 and rates .0003/.001; secondary mappings 55010–55014 retain their saved
order. Secondary trial dispatch requires the existing primary calibration Gate D.
The controller covers the **120-trial GRU training stage**. All **816 calibration
identities stay in the original ledger** and are not silently skipped, completed,
recalibrated or redesigned. Model/rate selection and calibration remain the existing
subsequent operations; this preparation does not execute them.

## Safeguards and observations

Before each session, two resource samples two seconds apart check available disk,
AC power and charging/stable battery state, OS thermal pressure and other Phase 11
workers. The controller preserves the previously measured full-artifact storage
allowance (63,904,146,368 bytes); it does not shrink the experimental budget.
An AC source label alone is insufficient when the battery reports discharging.
A `not charging` battery must have a stable percentage in consecutive samples.
Serious/critical OS thermal pressure blocks further dispatch. Unavailable thermal
pressure is logged, and is never presented as a measured temperature. If the process
inventory cannot be queried, production preflight fails closed.

A shared OS file lease covers the opt-in controller and the existing launcher's
CPU-heavy tasks. Only one trial child is spawned. Process checks additionally find
uncooperative/direct legacy workers; discovering a competing worker interrupts this
controller's child and leaves its existing checkpoint resumable. During a normal
trial, an unsafe resource reading prevents the next job from starting; the current
trial may finish and register normally. Ctrl-C/SIGTERM interrupts the worker and
publishes its latest committed checkpoint. No failed scientific trial is silently
retried or replaced with another seed.

Telemetry is sampled approximately every five seconds during work. It includes UTC
timestamps, trial IDs, wall durations, worker process CPU percentage/RSS where
available, battery/power, free disk, thermal-pressure state and competing workers.
Attempt/session records and observed cooling wait/deadline persist separately from
training checkpoints. No temperature in degrees C is inferred.

Live preparation preflight found **Battery Power, 70%, discharging**, with **nominal
NSProcessInfo thermal pressure**, no competing worker and adequate disk. It blocked
execution on AC/power state. Raw samples are in `preflight.json`. This observation
is dated evidence, not a promise about power or thermal conditions at a later run.

## Restart and result integrity

The trainer, Adam, input loader and checkpoint schema are unchanged. The controller
uses the existing parameters/moments/RNG/order/batch-offset/patience/best-state
checkpoint. An atomic scheduling journal records the active identity, completed
identities and original cooling deadline. Restarting retains the remaining cooling
interval rather than resetting it or repeating completed jobs.

Each completed trial is checked against its checkpoint, selected-weight hash, best
weights, report/history, full frozen train/validation identities, input-cache hashes,
configuration and tested sources before it is skipped. A report committed before
ledger registration is verified and registered exactly once without retraining.
Checkpoint generations are published before input/ledger registration. The same
verified temporary execution copy is retained across restarts, so output committed
by a child after abrupt parent death can be recovered once that child has exited.
A missing/tampered execution copy or changed sources blocks silent restart.

The journal is orchestration metadata; it is **not a new neural checkpoint format**.

## Validation actually executed

Final combined suite: **547 passed; 0 failures, errors or skips**, 27.706 seconds.
This comprises all **525 previously existing cases** and **22 new session cases**.
An earlier 545-case development run also passed before two additional crash-recovery
cases were added. Deterministic reruns are not independent scientific experiments.

Tests use mock jobs and a simulated clock, so 180-second intervals advance instantly.
They cover two-trial boundaries, serial deterministic order, cooling interruption,
trial interruption, no duplicate completion registration, failed-job blocking,
power/storage/pressure/process/RSS stops, missing thermal telemetry, process ownership,
exclusive lease release, persistent execution-copy reuse and publication ordering.

A synthetic-only controlled test uses the unchanged 321-input/16-hidden float64 GRU,
batch size 16, both registered rates, 24-step fixture episodes and three fixture epochs.
It interrupts after an update, resumes through the session controller, and compares
all parameters and learning histories exactly against the uninterrupted Phase 10
trainer. Production complete trials were **not** used as tests. No actual 180-second
cooling experiment or evidence of a temperature reduction is claimed.

The exact commands, XML/logs and source manifest are in `validation/*/`. The final
`readiness.json` binds **19 source/document hashes** to the passing suite. Historical
Phase 11 Gate B/evidence files remain unchanged; they describe the previous source
version. The sole edited existing source is `launch.py`, adding the shared worker
lease; its prior bytes are retained at `initial_sources/launch.py`. New modules and
one new test file implement the opt-in mode. No production checkpoints existed, and
no checkpoint migration or scientific configuration change was performed.

## Runtime projections

The acceleration audit measured a 1.615137666-second CPU median epoch including
validation and checkpoint writes. The following are projections under continuously
safe resource conditions, not completed work:

| Component | Projection |
| --- | --- |
| 120 trials, 21–200 epochs | 1.13–10.77 hours compute |
| Two trials per session | 60 sessions; about 1.13–10.77 minutes compute/session |
| 59 breaks × 180 seconds | **177 minutes / 2 hours 57 minutes** |
| GRU stage with cooling | **4.08–13.72 hours**, before extra controller overhead |
| Previously profiled Phase 11 components plus these breaks | **5.41–15.59 hours**, before unmeasured preparation/I/O and thermal variation |

Preflight adds approximately 2–4 minutes across 60 sessions, depending on how many
bounded launcher invocations are used. Input verification, worker startup and
incremental publication add unmeasured overhead. At primary/secondary phase
boundaries an already elapsed cooling deadline can reduce additional waiting;
the 59-break calculation assumes dedicated back-to-back training sessions. Resource
stops, offline time and human interruptions make an absolute worst-case duration
unbounded. Full calibration work is not itself batched by this GRU controller.

Two-trial cooling overhead is substantial: about 72% of projected earliest-stop
GRU-stage wall time, or 22% at the 200-epoch budget. Four trials/session would require
30 sessions and 29 breaks (87 minutes), saving 90 minutes, but would extend work
intervals to roughly 2.26–21.54 minutes. A later controlled four-trial thermal pilot
is a reasonable candidate if live telemetry supports it; its thermal safety is
unverified. **The implemented initial policy remains two trials**, as requested.

## Commands

Read-only live checks (default if no action flag is given):

```bash
./venv/bin/python -B -m connectome.scripts.phase11.session_launch --preflight
```

Re-run isolated engineering verification:

```bash
./venv/bin/python -B -m connectome.scripts.phase11.session_launch --validate
```

**For later explicit authorization only**, one bounded primary session:

```bash
./venv/bin/python -B -m connectome.scripts.phase11.session_launch --execute --scope primary --sessions 1
```

Invocation must have process-inventory access; the preparation preflight used
approved read-only execution outside the sandbox. Normal user terminal execution
is expected to expose this telemetry. Do not bypass a failed resource check.
No production command was executed during this preparation, and nothing continues
in the background. No dependency installation, GPU migration, commit or push occurred.

The original Phase 11 Gate B and blocked Gate C records remain historical evidence.
The opt-in launcher checks its own current `readiness.json` and live per-session
resource gates. The standard primary selection/calibration and later gates retain
their original requirements; refresh their versioned Gate B/C evidence for the
current sources and safe resources before using that standard workflow. Session
readiness does not declare Gate D, E or F complete or authorize held-out evaluation.
