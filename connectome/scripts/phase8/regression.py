"""Previous suites with all output routed into Phase 8."""
import argparse
from contextlib import redirect_stdout
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from .evidence import ROOT, OUT, write_json


def run(stage):
    output = OUT / "regression" / stage
    output.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, "-m", "pytest", "connectome/scripts/phase4/tests/",
               "connectome/phase5/tests/", "connectome/phase5_5/tests/", "connectome/phase6/tests/",
               "connectome/phase7/tests/", "-q", f"--junitxml={output / 'tests.xml'}"]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    (output / "tests.log").write_text(result.stdout + result.stderr)
    totals = {key: sum(int(s.attrib.get(key, 0)) for s in ET.parse(output / "tests.xml").getroot().iter("testsuite"))
              for key in ("tests", "failures", "errors", "skipped")}
    from connectome.scripts.phase4 import run_phase4_tests as suite
    original = suite.RESULTS_DIR
    try:
        suite.RESULTS_DIR = output
        with (output / "phase4_integration.log").open("w") as handle, redirect_stdout(handle):
            integration_code = suite.main()
    finally:
        suite.RESULTS_DIR = original
    assertions = json.loads((output / "phase4_test_results.json").read_text())["assertions"]
    evidence = dict(status="PASS" if result.returncode == 0 and integration_code == 0 else "FAIL",
                    command=command, tests=totals, exit_code=result.returncode,
                    phase4_assertions=assertions, integration_exit_code=integration_code)
    write_json(output / "summary.json", evidence)
    print(stage, evidence["status"], totals, assertions, flush=True)
    return evidence


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["before", "after"], required=True)
    if run(parser.parse_args().stage)["status"] != "PASS":
        raise SystemExit(1)
