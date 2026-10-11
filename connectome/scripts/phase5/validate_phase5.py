"""Run tests, regenerate samples and record reproducible validation evidence."""
from datetime import datetime, timezone
import hashlib
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from connectome.scripts.phase5.diagnostics import PHASE5, run_diagnostics

ROOT = PHASE5.parents[1]


def protected_hashes():
    paths = [ROOT / "connectome" / p for p in ("phase3", "scripts/phase3", "phase4", "scripts/phase4")]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in paths for p in sorted(folder.rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts}


def main():
    results = PHASE5 / "results"
    results.mkdir(parents=True, exist_ok=True)
    before = protected_hashes()
    command = [sys.executable, "-m", "pytest", "connectome/phase5/tests/", "-q",
               "--junitxml=connectome/phase5/results/unit_tests.xml"]
    run = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    (results / "unit_tests.txt").write_text(run.stdout + run.stderr)
    if run.returncode:
        print(run.stdout + run.stderr)
        raise SystemExit(run.returncode)
    suites = ET.parse(results / "unit_tests.xml").getroot().findall("testsuite")
    counts = {k: sum(int(s.attrib.get(k, 0)) for s in suites) for k in ("tests", "failures", "errors", "skipped")}
    log = io.StringIO()
    with redirect_stdout(log):
        diagnostics = run_diagnostics()
    (results / "diagnostics_output.txt").write_text(log.getvalue())
    print(log.getvalue().strip())
    after = protected_hashes()
    if before != after:
        raise AssertionError("Protected Phase 3/4 files changed")
    (results / "protected_file_hashes.json").write_text(json.dumps(before, indent=2) + "\n")
    evidence = dict(validated_at=datetime.now(timezone.utc).isoformat(),
        test_command="./venv/bin/python -m pytest connectome/phase5/tests/ -q --junitxml=connectome/phase5/results/unit_tests.xml",
        test_exit_code=run.returncode, test_counts=counts,
        protected_file_count=len(before), protected_files_unchanged=True,
        sample_count=len(diagnostics["samples"]), plot_count=len(diagnostics["plots"]))
    (results / "validation_results.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"Tests: {counts}; protected files unchanged: {len(before)}.")


if __name__ == "__main__":
    main()
