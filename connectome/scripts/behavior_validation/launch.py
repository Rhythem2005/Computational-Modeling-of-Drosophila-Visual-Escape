"""Verified historical namespace snapshot; never publishes to earlier phases."""
import fcntl
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

from .common import ROOT, read, sha, write, inventory, sources, MAX_BYTES, size

def snapshot():
    from connectome.scripts.phase10.launch import legacy_source
    expected = read(ROOT/'connectome/Results/phase9/results/preservation_before.json')
    expected.update(read(ROOT/'connectome/Results/phase9/results/delivery_artifact_index.json'))
    expected.update(read(ROOT/'connectome/Results/phase9/results/definition_lock.json')['sources_sha256'])
    for name in ('definition_lock.json', 'delivery_artifact_index.json'):
        expected['connectome/phase9/results/'+name] = sha(ROOT/'connectome/Results/phase9/results'/name)
    target = Path(tempfile.mkdtemp(prefix='fly-behavior-execution-'))
    copied = {}
    def copy(source, name):
        dest = target/name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
        copied[str(name)] = sha(source)
    for name, h in expected.items():
        source = ROOT/'connectome/Results/phase9/execution_baseline/README.md' if name == 'README.md' else legacy_source(name)
        if not source.is_file() or sha(source) != h:
            raise ValueError(f'Frozen legacy parent mismatch: {name}')
        copy(source, name)
    for base in ('connectome/Results/phase10', 'connectome/scripts/phase10',
                 'connectome/scripts/phase11', 'connectome/Results/phase11/repairs',
                 'connectome/scripts/behavior_validation'):
        for source in sorted((ROOT/base).rglob('*')):
            if source.is_file() and not {'__pycache__', '.pytest_cache'}.intersection(source.parts):
                copy(source, source.relative_to(ROOT))
    for name in ('README.md', 'training_plan.md', 'results/job_ledger.json'):
        p = ROOT/'connectome/Results/phase11'/name
        copy(p, p.relative_to(ROOT))
    production = ROOT/'connectome/Results/phase11/results'
    verified = read(ROOT/'connectome/Results/behavior_validation_planning_20261027/saved_state_verification.json')
    for selected in verified['selected']:
        f = read(ROOT/selected['freeze'])
        assert sha(ROOT/selected['freeze']) == selected['freeze_sha256']
        paths = [selected['freeze'], *f['artifacts_sha256']]
        mapping, seed = selected['mapping'], selected['seed']
        for rate in ('0p0003', '0p001'):
            folder = production/'training'/f'train_{mapping}_{seed}_{rate}'
            c = read(folder/'current.json')
            paths += [str((folder/n).relative_to(ROOT)) for n in ('current.json', 'report.json', 'selected.npz', c['arrays_file'])]
        for name in paths:
            copy(ROOT/name, name)
    # Fixed controls have their own calibrated freezes and bound input identities.
    for mapping in ('uniform_population', '55010'):
        for model, suffix in (('circuit', '_native'), ('feature_only', '')):
            name = f'connectome/Results/phase11/results/calibration/cal_{mapping}_{model}{suffix}/freeze.json'
            f = read(ROOT/name)
            for item in (name, *f['artifacts_sha256']):
                copy(ROOT/item, item)
    copy(ROOT/'connectome/Results/behavior_validation_planning_20261027/saved_state_verification.json',
         'connectome/Results/behavior_validation_planning_20261027/saved_state_verification.json')
    if size(target) > MAX_BYTES:
        raise RuntimeError('Snapshot exceeds artifact budget')
    return target, copied

def main():
    output = ROOT/'connectome/Results/behavior_validation'/str(time.time_ns())
    output.mkdir(parents=True, exist_ok=False)
    before = inventory(ROOT)
    write(output/'preservation_before.json', before)
    write(output/'authorization.json', dict(protocol='fly_behavior_neutral_fixture_v1',
          user_instruction='So now implement it also if there are any better ideas that may come up while implementing take those then.',
          scope='Approved bounded proposal: adapters, targeted checks, <=182 existing-fixture episodes; no training or held-out evaluation.',
          planning_sha256=sha(ROOT/'connectome/Results/behavior_validation_planning_20261027/README.md')))
    code = None
    try:
        # Read-only lease blocks concurrent training without rewriting its lock metadata.
        with (ROOT/'connectome/Results/phase11/results/manual_worker.lock').open('r') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            from connectome.scripts.phase11.runtime import sample, assess
            first = sample(); time.sleep(2); second = sample()
            errors = assess(first, second, MAX_BYTES)
            write(output/'resource_preflight.json', dict(samples=[first, second], blockers=errors,
                  disk_estimate_advisory=True, disk_warning=second['disk_free_bytes']<MAX_BYTES))
            if errors:
                raise RuntimeError('Resource startup gate: '+', '.join(errors))
            workspace, copied = snapshot()
            write(output/'snapshot.json', dict(path=str(workspace), files_sha256=copied,
                  actual_behavior_sources_sha256=sources(), bytes=size(workspace)))
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1',
                       OMP_NUM_THREADS='1', VECLIB_MAXIMUM_THREADS='1', MKL_NUM_THREADS='1',
                       FLY_BEHAVIOR_SNAPSHOT='1', FLY_BEHAVIOR_OUTPUT=str(output))
            command = [sys.executable, '-B', '-m', 'connectome.scripts.behavior_validation.run']
            print(f'Behavior output: {output}\nVerified execution snapshot: {workspace}', flush=True)
            with (output/'execution.log').open('w') as log:
                process = subprocess.Popen(command, cwd=workspace, env=env, stdout=log, stderr=subprocess.STDOUT)
                try:
                    code = process.wait(timeout=90*60)
                finally:
                    if process.poll() is None:
                        process.terminate()
                        try: process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill(); process.wait()
            # Even accidental writes to snapshot parent files invalidate the run.
            for name, h in copied.items():
                if sha(workspace/name) != h:
                    raise ValueError(f'Execution parent/source changed: {name}')
            write(output/'execution.json', dict(exit_code=code, snapshot=str(workspace), command=command,
                  execution_files_unchanged=True, snapshot_bytes=size(workspace)))
            fcntl.flock(lock, fcntl.LOCK_UN)
    except BaseException as error:
        write(output/'launcher_failure.json', dict(type=type(error).__name__, error=str(error)))
        raise
    finally:
        after = inventory(ROOT)
        write(output/'preservation_after.json', after)
        write(output/'preservation.json', dict(unchanged=before==after, files=len(before)))
        if before != after:
            raise ValueError('Protected original workspace changed')
    raise SystemExit(code)

if __name__ == '__main__':
    main()
