# Execution hold and validation handoff

**Status: awaiting user approval.** The requested frontend/backend source is written. No dashboard install, import/run, typecheck, build, test, preview, screenshot/browser session, server, simulation or training has been executed.

Repository inspection used read-only text/CSV/JSON/NPZ access to understand actual schemas and scientific contracts. Source edits are confined to `dashboard/`. Static source review is not a substitute for a passed build or runtime test.

## After explicit approval

1. Create the dashboard-local Python environment and install the declared backend/dev requirements. Install frontend dependencies and retain the generated lockfile. Leave the original scientific environment untouched.
2. Run backend unit/API tests from `dashboard/backend` with `../.venv/bin/python -B -m pytest tests`. These include path isolation, no-execution endpoints, producer authorization, missing-value handling, camera encoding and causal telemetry dimensions.
3. Run `npm test` and `npm run build` in `dashboard/frontend`. Resolve any dependency/type/browser compatibility failures before claiming readiness. Do not label historical 121 scientific checks as dashboard verification.
4. Start the read-only services. Inspect actual v2 circuit/hybrid, standalone, collision/no-action and earlier GRU/Phase 9 recordings. Compare cursor times with saved events; inspect the actual camera, channels, neural state, terminal behavior, null/missing values and hashes.
5. Verify orbit/follow/plan/circuit cameras, selection, archive/compare, scrubbing, slow motion, stepping, event seeking, looping, keyboard controls, fullscreen, narrow screens, reduced motion and WebGL failure fallback. Confirm display-only edge filters never alter science.
6. Verify live artifact discovery using an already independently authorized committed artifact; do not generate an experiment solely to exercise the UI without separate permission.
7. Exercise live ingestion only with an explicitly authorized source. Confirm wrong tokens, future timestamps, identity changes and unsupported state widths are rejected; disconnect/stop must not affect an experiment.
8. Recheck original scientific hashes and ensure all runtime artifacts remain inside dashboard-local dependency/build/cache locations. Do not commit/push unless separately requested.

Approval to launch the dashboard does not imply permission to run new simulations, resume 120-trial training, fit thresholds, consume independent/held-out cohorts, or reset exhausted experiment ledgers.
