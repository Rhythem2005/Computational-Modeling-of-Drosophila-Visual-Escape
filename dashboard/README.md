Current status (28 October 2026): **server stopped at the user's request**.
The room implementation and final software checks are documented in the
[final audit](docs/room_flight_final_audit_20261028/README.md) and
[room capabilities and limits](simulation/room_flight/README.md).

The built React frontend and FastAPI backend support room schema 1.0 and live
telemetry 1.2: canonical 3D solids, body quaternion, synchronized surrounding RGB,
recorded decisions/trajectories and separate front neural diagnostics. A labeled
geometry-only room design opens without selecting an archive. Explicit episode
links still open their original recording; click FLY to return to the room.
No experiment starts on page load.

The exact 24-attempt directional pilot is approved but **has not run**. Its earlier
startup was blocked at 18% battery, before reserving any attempt. Realistic generic
hand sensing, aerodynamic flight, a causal panoramic neural adapter and independent
behavioral validation remain separate work. Existing multi-object demonstrations
are development evidence only.

# Running dashboard

When the user requests a restart, use `bash dashboard/start.sh` from the repository
root, then open http://127.0.0.1:8001/?view=room. It serves the built frontend and
backend together, reusing dashboard-local installed dependencies and a private
producer token. This command does not launch simulations or training. The server
is deliberately left stopped after this audit.

The preparation-only status below is historical.

# FLY / Neural Observatory

An immersive React + Tailwind + Three.js observation chamber backed by FastAPI. **Built as source only; not installed, started, built or tested. Awaiting explicit execution approval.** All new files live inside `dashboard/`; scientific code, data, configuration, locks and results are unchanged.

## What is implemented

- A genuine interactive Three.js scene: procedural fruit fly, actual obstacle positions/radii, saved trajectories, contact state, observation aperture guide, orbit/follow/plan cameras and object inspection.
- Actual Circuit v2 connectivity (321 neurons, 11,557 directed edges), schematic 3-D node placement, clickable neurons, display-only edge filtering, and activity/input coloring from saved values.
- Correctly separated anatomical 321-unit activity, 16-unit GRU hidden state, and controllers with no recorded neural state. No fake neural activity, fabricated spikes or mock results.
- Synchronized camera imagery, encoder channels/drive, score/persistence traces, gate state, event markers, recorded geometry and movement, with a single playback clock. Physical geometry is interpolated only between recorded piecewise-linear world segments; neural/decoder/image observations use their own held timestamps.
- Play/pause, 1 ms stepping, timeline scrubbing, event navigation, speed, looping, controller/scenario selection, experiment archive, same-fixture comparisons, fullscreen, layer controls and provenance inspection.
- SHA-256 verification of each opened NPZ, Phase 9 companion-file checks, terminal-clock validation, bounded replay cache and read-only scientific integration.
- Automatic discovery of new committed recordings, plus an optional authenticated external live-telemetry interface. Existing runners return complete episodes rather than expose a live observer, so their results are **synchronized replay**, not falsely labeled live simulation.

## Scientific fidelity

The existing physics is planar. It is rendered in a 3-D environment as `(world_x, 0, -world_y)`; this dashboard does not invent altitude, yaw, biomechanics or 3-D scientific dynamics. Arena height, lighting, fly mesh/wing shape and schematic neural positions are display-only. The fly's wireframe collision boundary and obstacle radii come from the actual config. Sensor images come directly from the saved NPZ, not from the observation camera.

Edge brightness is a visual encoding of source activity weighted by recorded structural weight, not a measured synaptic current. The graph shows up to 1,800 filtered edges for GPU performance; full connectivity is available from the API, and selected-neuron counts use all edges. Display filters never modify the model. Unknown perception and absent neural traces stay unknown/absent.

The archive reads Phase 9, behavioral comparison, collision-threat v1 and collision-threat v2 recordings. It never scans open-loop held-out cohorts or training-score caches. Saved ledger totals are not claims about a currently running worker. Known development-fixture results are not independent generalization evidence.

## After approval: setup

Requirements: Python 3.11+ and Node **20.19+** (or a compatible newer LTS). Use a dashboard-local environment; do not install into or alter the scientific environment.

```bash
# From the FLY repository root; NOT executed during preparation.
python3 -m venv dashboard/.venv
dashboard/.venv/bin/python -m pip install -r dashboard/backend/requirements-dev.txt
cd dashboard/frontend
npm install
```

The first approved npm install generates a lockfile. No invented lockfile or claim of resolved/verified dependencies is supplied. React 19 is paired with React Three Fiber 9; Tailwind 4 uses its Vite plugin. No downloaded models or remote runtime images are required.

After setup and launch approval, from the repository root:

```bash
bash dashboard/start-dev.sh
```

Frontend: `http://127.0.0.1:5173`; API: `http://127.0.0.1:8000/api/v1/health`; interactive API contracts: `http://127.0.0.1:8000/docs`. Ctrl+C stops the web services. The launcher has **no installation or experiment side effects**. For separate terminals:

```bash
cd dashboard/backend
PYTHONDONTWRITEBYTECODE=1 ../.venv/bin/python -B -m uvicorn fly_dashboard.main:app --host 127.0.0.1 --port 8000
```

```bash
cd dashboard/frontend
npm run dev
```

The default repository root is derived from the backend's file location. Optional environment configuration is documented in `.env.example`; it must be exported by the caller (the service does not silently load secrets). Frontend `VITE_API_BASE` can point to another approved API host; otherwise Vite proxies `/api`, including WebSockets.

For a production build **only after approval**, run `npm run build` in `dashboard/frontend`, then start the backend. FastAPI serves the built `frontend/dist/` if present. No hosting/deployment is configured.

## Live and future experiments

1. A producer's committed metadata/NPZ pair under a supported result directory is discovered automatically within the catalog refresh interval. Incomplete or malformed pairs appear in diagnostics, not as invented outcomes.
2. Additional directories can be declared using `FLY_DASHBOARD_EXTRA_SOURCES`, a JSON list of paths under `connectome/Results`. They must use a supported schema and bind `arrays_sha256` to the actual NPZ. Paths outside scientific results are rejected.
3. An independently approved real-time producer can use `backend/fly_dashboard/producer.py`. It sends actual observations to the backend; the dashboard does not import or start scientific runners. Enable ingestion with an environment-only `FLY_DASHBOARD_INGEST_TOKEN`; without it, ingestion is disabled. The UI never contains the producer token.
4. Live sessions are bounded, in-memory and explicitly marked external/unverified. One session has stable object/state identities and strictly increasing time; reset means a new session. The UI can switch to it from the archive. Ending/removing a telemetry session does not stop an experiment process.

See [API and extension contract](docs/API.md), [project analysis](docs/PROJECT_ANALYSIS.md), and [validation/approval handoff](docs/VALIDATION.md). No new scientific live-loop adapter has been executed or substituted into the frozen pipeline.

## Controls

Space: play/pause. Left/right arrows: ±1 ms. Home: replay start. F: reset observation camera. C: circuit focus. Drag: orbit, scroll: zoom. Click the fly, object or neuron for actual recorded values. Archive/compare controls change recordings; they never run a new experiment. Live producer mode disables replay transport because it is showing received observations.

## Validation status

Test files are included but **not run**. No npm install, build, typecheck, pytest, preview, server, simulation, training, calibration, held-out evaluation, commit or push was performed. Runtime correctness, browser layout/performance and dependency resolution remain to be verified after approval. Do not interpret historical scientific test counts as dashboard test results.
