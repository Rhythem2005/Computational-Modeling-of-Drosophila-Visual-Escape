"""Gate B verification in disposable copies; retain exact logs and counts."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from connectome.scripts.phase10.regression import counts
from .common import ROOT, OUT, write, sources


def verify():
    child = Path(tempfile.mkdtemp(prefix='fly-phase11-tests-'))/'repo'
    shutil.copytree(ROOT, child, ignore=shutil.ignore_patterns('__pycache__', '.pytest_cache'))
    directory = OUT/'engineering'/str(time.time_ns())
    directory.mkdir(parents=True, exist_ok=True)
    targets = ['connectome/scripts/phase11/tests', 'connectome/Results/phase10/tests',
               'connectome/scripts/phase4/tests',
               *[f'connectome/{p}/tests' for p in ('phase5', 'phase5_5', 'phase6', 'phase7', 'phase8', 'phase8/completion', 'phase9')]]
    command = [sys.executable, '-m', 'pytest', *targets, '-q', '-p', 'no:cacheprovider', f'--junitxml={directory/"tests.xml"}']
    start = time.perf_counter()
    result = subprocess.run(command, cwd=child, capture_output=True, text=True)
    (directory/'tests.log').write_text(result.stdout+result.stderr)
    summary = dict(status='PASS' if result.returncode == 0 else 'FAIL', tests=counts(directory/'tests.xml'),
                   command=command, exit_code=result.returncode, runtime_s=time.perf_counter()-start,
                   phase11_sources_sha256=sources(), isolation='All output-writing tests in disposable child copy',
                   benchmark_training_runs=0, benchmark_calibrations=0, held_out_inference_runs=0)
    write(directory/'summary.json', summary)
    write(OUT/'gate_B.json', summary)
    print('Gate B:', summary['status'], summary['tests'], flush=True)
    if result.returncode:
        raise ValueError(f'Engineering tests failed; see {directory}/tests.log')
    return summary
