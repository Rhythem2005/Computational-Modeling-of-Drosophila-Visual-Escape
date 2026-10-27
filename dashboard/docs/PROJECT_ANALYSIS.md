# Existing FLY integration analysis

Prepared from repository/source and saved-artifact inspection before and during implementation. No application, simulator, training, calibration, test or build was executed to produce this dashboard.

## Pipeline mapping

| Existing subsystem | Evidence/source inspected | Dashboard integration |
| --- | --- | --- |
| Dataset and circuit freeze, Phases 0–3 | Phase 3 circuit JSON, nodes/edges CSV, provenance and project overview | Actual node identities, populations, structural synapse counts, edge categories and source hashes. There are no anatomical node coordinates in these CSVs; the graph layout is explicitly schematic. |
| Phase 4 neural dynamics | `scripts/phase4`, simulator README | Read saved activity. No simulator imports, model reconstruction or re-execution in the service. Rate activity is not presented as spikes. |
| Phase 5/5.5 stimuli and protocol | Benchmark and phase-level documentation | Explain provenance and keep scientific generation/partition decisions outside presentation. No test/OOD directory discovery. |
| Phase 6 encoder | Encoder/config and actual NPZ channel/drive fields | Synchronized LC4-like/LPLC2-like channels, per-body input drive, camera validity and saved frame IDs. Missing/invalid inputs are visible. |
| Phase 7 causal integration | `pipeline.py`, `MillisecondInput`, clocks/state-before-update contract | Neural state and decoder decision clocks remain independent. No future neural state is substituted for a held sample. |
| Phase 8 decoder | Streaming persistence, threshold and first-event contracts | Actual raw/sustained scores and events. Subnormal thresholds stay intact in JSON and scientific notation. |
| Phase 9 world | `world.py`, `activity_io.py`, actual stored schema | Actual disk radii and 2-D coordinates represented in an interactive 3-D observation environment. Legacy split JSON companions and their hashes supported. |
| Phase 10/11 controls and training | GRU forward/state timing, ledger, checkpoint interfaces | Distinguish 321 anatomical neurons, 16 GRU units and no neural state. Read saved ledger completion totals; do not infer live process state from historical blockers or RUNNING rows. |
| Behavioral comparison | `behavior_validation` records and schema | Saved circuit, GRU, simple-trigger and no-action runs; paired comparison and replay. |
| Collision-threat v1 | Features, hybrid, geometric rule, runner, recording | Image/decision/gate/motion alignment and explicit unknown/fallback events. |
| Collision-threat v2 | Runner, driver, recording, latest report/summary | Candidate retirement/re-arm events and known-size assumptions; real finite-body and revised-gate results are not fabricated or re-evaluated. |

## Concrete stored formats inspected

- Phase 9: schema `1.0`, split `_metadata`, `_config`, `_action`, `_metrics` JSON; `states`, `neural_times_ms`, `score`, `world_times_ms`, physical trajectories and 60 grayscale camera frames.
- Behavioral GRU: `behavior_1.0`; `controller_states` has 16 columns, while `body_ids` and input drive still describe 321 anatomical input coordinates. Hidden units must not be painted onto the anatomical circuit.
- v1: `collision_threat_1.0`; compact metadata JSON and bound NPZ, neural/measurement/decision clocks, raw/sustained scores and physical/internal request separation.
- v2: `collision_threat_2.0`; anatomical hybrid state can be `(1001,321)`, standalone state `(1001,0)`. Gate state, epochs, retirement/re-arm and unknown-after-retirement arrays are saved. Zero-width neural state is unavailable, not zero-valued fabricated activity.
- World data terminates at actual physical contact, including fractional contact; decisions exclude the terminal time and 1000 ms. Camera samples can exist after the last completed neural update; the camera and controller-input indices are displayed according to their own clocks.

## Current scientific evidence

The latest v2 run has 80 attempts (40 combinations and 40 exact repeats) on five known geometries. Its recorded 121 checks are historical scientific checks, not dashboard checks. Revised hybrid gates avoid the three dangerous fixtures and request on neither harmless fixture. The original fallback gates retain the late 767 ms near-miss false alarm. Finite-body handling uses a fixed object-size prior; its benefit on novel finite-body-only contacts is not established by these five cases.

Training remains an incomplete conventional-model comparison: saved totals 45/120 trials and 272/816 calibrations. More GRU fitting does not update anatomical weights or movement. Some root/older README roadmap/status text is historical; latest ledger and run artifacts take precedence for the displayed saved state.

## Architectural conclusions

The current synchronous runners return complete arrays. Their heartbeat does not expose a full per-step observation interface, and exhausted experiment ledgers cannot be reused to populate a UI. Consequently the dashboard provides verified synchronized replay for existing runs and read-only discovery of newly committed artifacts. Real-time external telemetry is a separately labeled optional presentation interface, not a silently modified scientific runner.

All artifact discovery is confined to known closed-loop result roots (or caller-declared additional roots under `connectome/Results`). IDs are opaque hashes of relative metadata paths, not arbitrary browser-supplied filesystem paths. NPZ loading disables pickle. No endpoint starts experiments, resumes checkpoints, generates stimuli or changes scientific results.

## UI design

The main canvas is the working environment, not a decorative fly next to a conventional dashboard. World objects, trajectories, the subject and neural schematic are selectable in 3-D. Floating optical/telemetry instruments, a small spatial toolbar and a single transport retain context. The same replay clock drives every view; GPU display filters have no scientific effect.

## Framework references

The source dependency pairing follows [React Three Fiber's React 19 / Fiber 9 compatibility guidance](https://r3f.docs.pmnd.rs/getting-started/installation). Tailwind uses the [official Vite plugin workflow](https://tailwindcss.com/docs/installation/using-vite). Live channels follow [FastAPI's WebSocket interface](https://fastapi.tiangolo.com/advanced/websockets/). Dependencies have not been installed/resolved and runtime compatibility remains unverified pending approval.
