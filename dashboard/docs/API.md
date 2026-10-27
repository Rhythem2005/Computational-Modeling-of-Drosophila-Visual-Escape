# Read-only API and future telemetry contract

Base `/api/v1`. Server creation imports only dashboard code, FastAPI/Pydantic and NumPy. Repository scanning starts in application lifespan after approved launch. Original simulator, training and launcher modules are never imported. Generated camera PNG bytes and caches are in memory.

| Endpoint | Purpose |
| --- | --- |
| GET `/health` | Read-only capabilities; scientific execution is false |
| GET `/catalog` | Discover complete closed-loop metadata/NPZ pairs; per-source parse diagnostics |
| WS `/catalog/ws` | Notify viewers of new committed artifacts; heartbeat when unchanged |
| GET `/status` | Saved training/calibration totals and limitations; worker status explicitly unobserved |
| GET `/connectome` | Actual Circuit v2 nodes/edges and structural-file hashes |
| GET `/episodes/{opaque_id}/replay` | Verified clocks, world, neural, encoder, decisions, measurements, metrics and events |
| GET `/episodes/{opaque_id}/camera.png` | Atlas generated from actual stored grayscale frames; browser crops the current sample |
| GET `/live` | Current external producer sessions |
| POST `/live` | Token-protected creation of an external telemetry session |
| POST `/live/{id}/frames` | Token-protected actual observed frame publication |
| WS `/live/{id}/ws` | Read-only viewer subscription, bounded history and current frames |
| POST `/live/{id}/end` | Producer marks telemetry ended, not an experiment-process stop |
| DELETE `/live/{id}` | Remove an ended, detached in-memory session |

There is no run, train, calibrate, tune, write-artifact, arbitrary-file or shell endpoint. All HTTP routes and schemas are documented by FastAPI at `/docs` after launch.

## Replay shape

The replay JSON has `episode`, `config`, `scenario`, `metrics`, `integrity`, `world`, `neural`, `decision`, `encoder`, `measurements`, `camera`, `events` and `duration_ms`. All times are explicitly milliseconds, except raw NPZ frame times converted from their saved seconds. World coordinate arrays retain their original two coordinates. The frontend maps them to display X/−Z, not new physical altitude.

Neural `kind` is `anatomical`, `gru_hidden`, or `unavailable`. `ids` align with columns. Encoder IDs are separately supplied because a GRU's 16 hidden IDs do not describe its 321 inputs. Missing/nonfinite diagnostic fields become JSON null, not fabricated zeros. The SHA-256, schema and source path identify the selected recording.

Backend sources currently cover Phase 9, `behavior_validation`, `collision_threat_v1/prototype` and `collision_threat_v2/runs`. Add future committed directories using the environment source list, or add a new explicitly documented adapter if a future schema changes clocks or dimensions. Do not coerce a genuinely 3-D experiment into this planar schema.

## Real-time observer extension

Enable ingestion with `FLY_DASHBOARD_INGEST_TOKEN` in the backend environment; callers supply `X-Fly-Ingest-Token`. Keep that credential out of frontend code and scientific artifacts. Sessions are in-memory, capped at four, with 200 recent frames and bounded viewer queues. Rendering cannot backpressure the scientific producer through WebSocket queues. The supplied HTTP helper is synchronous; connect it through a bounded independent observer queue and handle network failures outside a scientific decision loop.

Use `DashboardPublisher` from `backend/fly_dashboard/producer.py` only within an independently approved experiment/observer. Pass its actual source/configuration to `open(name=..., protocol=..., controller=..., source_note=..., world_config=...)`. Call `publish` with copies of actual observations:

- `time_ms`: finite, monotonic episode clock; resetting requires a new session.
- `fly`: actual `[x,y]`; `obstacles`: stable IDs, positions and actual evaluator radii.
- Optional actual `speed`, `score`, `sustained_score`, `gate_state`, `rule_state`, encoder channels/validity and input drive.
- `encoder_body_ids`: 321 ordered unique IDs if input drive is supplied.
- `neural_kind`, `neural_ids`, `neural_values`: 321 matched actual anatomical states, 16 actual hidden units, or unavailable/empty. Do not manufacture a neural response for a rule-only controller.
- Optional actual PNG camera frame as base64 plus its observation timestamp. Frames cannot come from the future.
- Actual events only; event timestamps must not exceed the published clock.

The dashboard always labels this mode external/unverified rather than SHA-verified replay. A session does not receive a manufactured experiment result or collision label. No existing source code is changed to attach a producer automatically; unchanged frozen runners remain replay sources.
