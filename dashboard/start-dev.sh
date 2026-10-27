#!/usr/bin/env bash
# Do not invoke until launch approval. This starts web services, never experiments.
set -euo pipefail
dashboard_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ ! -x "$dashboard_dir/.venv/bin/python" || ! -d "$dashboard_dir/frontend/node_modules" ]]; then
  echo "Dashboard dependencies are not installed. Follow dashboard/README.md after approval."
  exit 1
fi
export PYTHONDONTWRITEBYTECODE=1
(cd "$dashboard_dir/backend" && "$dashboard_dir/.venv/bin/python" -B -m uvicorn fly_dashboard.main:app --host 127.0.0.1 --port 8000) &
dashboard_backend_pid=$!
trap 'kill "$dashboard_backend_pid" 2>/dev/null || true' EXIT INT TERM
cd "$dashboard_dir/frontend"
npm run dev
