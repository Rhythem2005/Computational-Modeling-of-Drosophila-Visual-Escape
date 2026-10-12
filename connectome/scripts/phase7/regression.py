"""Run earlier read-only checks; route all new evidence into Phase 7."""
import argparse
from contextlib import redirect_stdout
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from .evidence import OUT, ROOT, write_json


def run(stage):
    output = OUT / "regression" / stage
    output.mkdir(parents=True, exist_ok=True)
    commands = [
        [sys.executable, "-m", "pytest", "connectome/scripts/phase4/tests/", "connectome/phase5/tests/",
         "connectome/phase5_5/tests/", "connectome/phase6/tests/", "-q", f"--junitxml={output / 'tests.xml'}"],
    ]
    if stage == "before":
        commands += [[sys.executable, "-m", f"connectome.scripts.{module}"] for module in
                     ("phase1.verify_phase1", "phase2.verify_phase2", "phase3.verify_circuit_v2", "phase3.independent_audit_verifier")]
    records = []
    for i, command in enumerate(commands):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        log = output / f"command_{i}.log"
        log.write_text(result.stdout + result.stderr)
        records.append(dict(command=command, exit_code=result.returncode, log=str(log.relative_to(ROOT))))
        print(f"{stage}: {command[2:]} exit={result.returncode}", flush=True)
    counts = {key: 0 for key in ("phase4", "phase5", "phase5_5", "phase6")}
    for case in ET.parse(output / "tests.xml").getroot().iter("testcase"):
        name = case.attrib["classname"]
        key = next(k for k in ("phase5_5", "phase6", "phase5", "phase4") if k in name)
        counts[key] += 1
    from connectome.scripts.phase4 import run_phase4_tests as suite
    old = suite.RESULTS_DIR
    try:
        suite.RESULTS_DIR = output
        with (output / "phase4_integration.log").open("w") as handle, redirect_stdout(handle):
            code = suite.main()
    finally:
        suite.RESULTS_DIR = old
    assertions = json.loads((output / "phase4_test_results.json").read_text())["assertions"]
    summary = dict(commands=records, unit_test_counts=counts, phase4_assertions=assertions,
                   phase4_integration_exit_code=code, status="PASS" if code == 0 and all(r["exit_code"] == 0 for r in records) else "FAIL")
    write_json(output / "summary.json", summary)
    print(summary["status"], counts, assertions, flush=True)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["before", "after"], required=True)
    args = parser.parse_args()
    if run(args.stage)["status"] != "PASS":
        raise SystemExit(1)
