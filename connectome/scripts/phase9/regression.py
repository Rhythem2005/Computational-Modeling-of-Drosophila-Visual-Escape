"""Existing tests without invoking earlier validators or writing earlier outputs."""
import argparse
from contextlib import redirect_stdout
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from .config import OUT
from .evidence import ROOT, write_json


def run(stage):
    directory=OUT / "regression" / stage; directory.mkdir(parents=True,exist_ok=True)
    command=[sys.executable,"-m","pytest","connectome/scripts/phase4/tests/","connectome/phase5/tests/",
             "connectome/phase5_5/tests/","connectome/phase6/tests/","connectome/phase7/tests/","connectome/phase8/tests/",
             "connectome/phase8/completion/tests/","-q",f"--junitxml={directory / 'tests.xml'}"]
    result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
    (directory / "tests.log").write_text(result.stdout+result.stderr)
    counts={k:sum(int(s.attrib.get(k,0)) for s in ET.parse(directory / "tests.xml").getroot().iter("testsuite")) for k in ("tests","failures","errors","skipped")}
    from connectome.scripts.phase4 import run_phase4_tests as suite
    original=suite.RESULTS_DIR
    try:
        suite.RESULTS_DIR=directory
        with (directory / "phase4_integration.log").open("w") as f,redirect_stdout(f):
            integration=suite.main()
    finally:
        suite.RESULTS_DIR=original
    assertions=json.loads((directory / "phase4_test_results.json").read_text())["assertions"]
    report=dict(status="PASS" if result.returncode == integration == 0 else "FAIL",command=command,tests=counts,phase4_assertions=assertions,
                exit_code=result.returncode,integration_exit_code=integration)
    write_json(directory / "summary.json",report); print(stage,report["status"],counts,assertions,flush=True)
    return report


if __name__ == "__main__":
    p=argparse.ArgumentParser();p.add_argument("--stage",choices=["before","after"],required=True)
    if run(p.parse_args().stage)["status"] != "PASS": raise SystemExit(1)
