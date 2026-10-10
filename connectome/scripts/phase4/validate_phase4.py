"""Run the complete Phase 4 acceptance pipeline and save its evidence."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
RESULTS_DIR = PROJECT_ROOT / "connectome" / "phase4" / "results"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    python = sys.executable
    commands = [
        ("phase4_unit_tests", [python, "-m", "pytest", "-p", "no:cacheprovider", "connectome/scripts/phase4/tests/test_phase4.py", "-q"]),
        ("phase3_circuit_v2", [python, "connectome/scripts/phase3/verify_circuit_v2.py"]),
        ("phase3_independent_audit", [python, "connectome/scripts/phase3/independent_audit_verifier.py"]),
        ("phase3_archival_v1", [python, "connectome/scripts/phase3/verify_circuit_v1.py"]),
        ("phase4_integration", [python, "connectome/scripts/phase4/run_phase4_tests.py"]),
        ("phase4_analysis", [python, "connectome/scripts/phase4/analyze_phase4.py"]),
        ("phase4_plots", [python, "connectome/scripts/phase4/generate_plots.py"]),
    ]
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["MPLCONFIGDIR"] = str(Path(tempfile.gettempdir()) / "fly-phase4-matplotlib")
    manifest = {"run_date": datetime.now(timezone.utc).isoformat(), "commands": []}
    overall_exit = 0
    for label, command in commands:
        completed = subprocess.run(
            command, cwd=PROJECT_ROOT, env=environment, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
        )
        output_path = RESULTS_DIR / f"{label}.txt"
        output_path.write_text(completed.stdout)
        match = re.search(r"(\d+) passed", completed.stdout)
        manifest["commands"].append({
            "label": label,
            "command": command,
            "exit_code": completed.returncode,
            "output_file": str(output_path.relative_to(PROJECT_ROOT)),
            "output_sha256": _sha256(output_path),
            "pytest_passed": int(match.group(1)) if match else None,
        })
        print(f"[{label}] exit={completed.returncode}")
        if completed.returncode != 0:
            overall_exit = 1
    manifest["status"] = "PASS" if overall_exit == 0 else "FAIL"
    manifest_path = RESULTS_DIR / "validation_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"Validation manifest: {manifest_path}")
    return overall_exit


if __name__ == "__main__":
    sys.exit(main())
