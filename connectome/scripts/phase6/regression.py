"""Run existing suites, routing all evidence to Phase 6 only."""
from contextlib import redirect_stdout
import json
import subprocess
import xml.etree.ElementTree as ET
from .encoder import ROOT, PHASE


def main():
    output = PHASE / "results/regression"
    output.mkdir(parents=True,exist_ok=True)
    command = [str(ROOT/"venv/bin/python"),"-m","pytest","connectome/scripts/phase4/tests/",
        "connectome/phase5/tests/","connectome/phase5_5/tests/","-q",f"--junitxml={output/'baseline.xml'}"]
    run = subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
    (output/"baseline.log").write_text(run.stdout+run.stderr)
    if run.returncode: raise RuntimeError(run.stdout+run.stderr)
    xml = ET.parse(output/"baseline.xml").getroot()
    counts = {"phase4":0,"phase5":0,"phase5_5":0}
    for case in xml.iter("testcase"):
        name = case.attrib["classname"]
        key = "phase5_5" if "phase5_5" in name else "phase5" if "phase5" in name else "phase4"
        counts[key] += 1
    # Existing regression suite only; not visual-to-circuit pipeline work.
    from connectome.scripts.phase4 import run_phase4_tests as suite
    old_dir = suite.RESULTS_DIR
    try:
        suite.RESULTS_DIR = output
        with (output/"phase4_integration.log").open("w") as handle, redirect_stdout(handle):
            code = suite.main()
    finally:
        suite.RESULTS_DIR = old_dir
    assertions = json.loads((output/"phase4_test_results.json").read_text())["assertions"]
    evidence = dict(unit_tests=counts,unit_failures=0,phase4_integration=assertions,
        expected_phase4_assertions=159,expected_phase5_tests=114,
        count_discrepancy=assertions["total"] != 159 or counts["phase5"] != 114)
    (output/"summary.json").write_text(json.dumps(evidence,indent=2)+"\n")
    print(f"Regression: {counts}; integration {assertions}; discrepancies={evidence['count_discrepancy']}")
    if code: raise RuntimeError("Phase 4 regression failed")


if __name__ == "__main__": main()
