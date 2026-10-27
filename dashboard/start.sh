#!/usr/bin/env bash
set -euo pipefail
dashboard_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONDONTWRITEBYTECODE=1
export FLY_DASHBOARD_ORIGINS="${FLY_DASHBOARD_ORIGINS:-http://127.0.0.1:8001,http://localhost:8001}"
if [[ ! -x "$dashboard_dir/.venv/bin/python" || ! -f "$dashboard_dir/frontend/dist/index.html" ]]; then
  echo "Dashboard environment or frontend build missing. See dashboard/README.md."
  exit 1
fi
# Reuse a private local credential; never expose it in the frontend or logs.
if [[ -z "${FLY_DASHBOARD_INGEST_TOKEN+x}" ]]; then
  "$dashboard_dir/.venv/bin/python" - "$dashboard_dir/.runtime/ingest-token" <<'PY'
import os, secrets, sys
from pathlib import Path
p=Path(sys.argv[1]);p.parent.mkdir(parents=True,exist_ok=True)
try:
    fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
except FileExistsError:
    if p.is_symlink() or not p.read_text().strip():raise SystemExit('Invalid local telemetry credential file')
    os.chmod(p,0o600)
else:
    with os.fdopen(fd,'w') as f:f.write(secrets.token_urlsafe(32))
PY
  FLY_DASHBOARD_INGEST_TOKEN="$(cat "$dashboard_dir/.runtime/ingest-token")"
fi
export FLY_DASHBOARD_INGEST_TOKEN
cd "$dashboard_dir/backend"
exec "$dashboard_dir/.venv/bin/python" -B -m uvicorn fly_dashboard.main:app --host 127.0.0.1 --port 8001
