"""Run unchanged earlier tests in a disposable child copy, retaining only logs."""
from contextlib import redirect_stdout
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from .common import ROOT, OUT, write_json


def counts(path):
    return {k:sum(int(s.attrib.get(k,0)) for s in ET.parse(path).getroot().iter('testsuite')) for k in ('tests','failures','errors','skipped')}


def run(stage):
    child=Path(tempfile.mkdtemp(prefix='fly-phase10-regression-'))/'repo'
    shutil.copytree(ROOT,child,ignore=shutil.ignore_patterns('__pycache__','.pytest_cache'))
    command=[sys.executable,'-m','connectome.scripts.phase10.regression',stage]
    result=subprocess.run(command,cwd=child,capture_output=True,text=True)
    source=child/'connectome/Results/phase10/results/regression'/stage
    target=OUT/'regression'/stage
    if source.exists():shutil.copytree(source,target,dirs_exist_ok=True)
    if result.returncode:raise RuntimeError(f'Earlier regression failed: {result.stdout} {result.stderr}')
    return json.loads((target/'summary.json').read_text())


def worker(stage):
    directory=OUT/'regression'/stage;directory.mkdir(parents=True,exist_ok=True)
    targets=['connectome/scripts/phase4/tests',*[f'connectome/{p}/tests' for p in ('phase5','phase5_5','phase6','phase7','phase8','phase8/completion','phase9')]]
    command=[sys.executable,'-m','pytest',*targets,'-q','-p','no:cacheprovider',f'--junitxml={directory/"tests.xml"}']
    result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
    (directory/'tests.log').write_text(result.stdout+result.stderr)
    from connectome.scripts.phase4 import run_phase4_tests as suite
    original=suite.RESULTS_DIR
    try:
        suite.RESULTS_DIR=directory
        with (directory/'phase4_integration.log').open('w') as f,redirect_stdout(f):integration=suite.main()
    finally:suite.RESULTS_DIR=original
    assertions=json.loads((directory/'phase4_test_results.json').read_text())['assertions']
    summary=dict(status='PASS' if result.returncode==integration==0 else 'FAIL',tests=counts(directory/'tests.xml'),phase4_assertions=assertions,
                 command=command,exit_code=result.returncode,integration_exit_code=integration,
                 isolation='Disposable copy; all original and main-execution earlier artifacts preserved')
    write_json(directory/'summary.json',summary)
    return 0 if summary['status']=='PASS' else 1


if __name__=='__main__':raise SystemExit(worker(sys.argv[1]))
