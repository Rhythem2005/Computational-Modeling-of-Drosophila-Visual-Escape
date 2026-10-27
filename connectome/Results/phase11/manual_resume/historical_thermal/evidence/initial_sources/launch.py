"""Reconstruct Phase 10's byte-verified legacy namespace without writing parents."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from .common import ROOT, BASE, OUT, sha, read, write, protected, sources, atomic
from connectome.scripts.phase10.launch import legacy_source


def snapshot():
    expected = read(ROOT/'connectome/Results/phase9/results/preservation_before.json')
    expected.update(read(ROOT/'connectome/Results/phase9/results/delivery_artifact_index.json'))
    expected.update(read(ROOT/'connectome/Results/phase9/results/definition_lock.json')['sources_sha256'])
    for name in ('definition_lock.json', 'delivery_artifact_index.json'):
        expected['connectome/phase9/results/'+name] = sha(ROOT/'connectome/Results/phase9/results'/name)
    target = Path(tempfile.mkdtemp(prefix='fly-phase11-execution-'))
    for name, value in expected.items():
        source = ROOT/'connectome/Results/phase9/execution_baseline/README.md' if name == 'README.md' else legacy_source(name)
        if not source.is_file() or sha(source) != value:
            raise ValueError(f'Frozen legacy parent mismatch: {name}')
        dest = target/name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
    for source in (ROOT/'connectome/Results/phase10', ROOT/'connectome/scripts/phase10', BASE, ROOT/'connectome/scripts/phase11'):
        shutil.copytree(source, target/source.relative_to(ROOT), ignore=shutil.ignore_patterns('__pycache__', '.pytest_cache'), dirs_exist_ok=True)
    return target, len(expected)


def publish(source, destination):
    """Commit referenced checkpoint arrays before publishing their JSON pointer."""
    source, destination = Path(source), Path(destination)
    pointers = list(source.rglob('current.json'))
    checkpoint_dirs = {p.parent for p in pointers}
    for pointer in pointers:
        # Capture one committed pointer; never chase a moving generation mid-copy.
        raw = pointer.read_bytes()
        import json
        record = json.loads(raw)
        payload = pointer.parent/record['arrays_file']
        try:
            data = payload.read_bytes()
        except FileNotFoundError:
            continue  # Writer advanced two generations; retry next publication.
        import hashlib
        if hashlib.sha256(data).hexdigest() != record['arrays_sha256']:
            raise ValueError('Checkpoint publication hash mismatch')
        target_dir = destination/pointer.parent.relative_to(source)
        atomic(target_dir/payload.name, data)
        atomic(target_dir/pointer.name, raw)
        for old in target_dir.glob('state_*.npz'):
            if int(old.stem.split('_')[1]) < record['generation']-1:
                old.unlink()
    for p in source.rglob('*'):
        if not p.is_file() or p.name == 'current.json' or (p.parent in checkpoint_dirs and p.name.startswith('state_')):
            continue
        target = destination/p.relative_to(source)
        if not target.exists() or sha(p) != sha(target):
            atomic(target, p.read_bytes())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--task', choices=['integrity', 'engineering', 'profile', 'primary', 'secondary', 'freeze'], required=True)
    args = parser.parse_args()
    before = protected()
    write(OUT/'preservation_before.json', before, immutable=True)
    workspace, count = snapshot()
    command = [sys.executable, '-m', 'connectome.scripts.phase11.runner', '--task', args.task]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', MPLCONFIGDIR='/tmp/fly-phase11-mpl',
               OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', VECLIB_MAXIMUM_THREADS='1')
    write(OUT/'execution_current.json', dict(task=args.task, snapshot=str(workspace), command=command,
          legacy_files_verified=count, sources_sha256=sources()))
    print(f'Phase 11 {args.task}: isolated workspace {workspace}', flush=True)
    code = None
    try:
        process = subprocess.Popen(command, cwd=workspace, env=env)
        # Publish atomic checkpoint generations incrementally, including on failure.
        while True:
            try:
                code = process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                pass
            publish(workspace/'connectome/Results/phase11/results', OUT)
            if code is not None:
                break
    finally:
        after = protected()
        write(OUT/'preservation_after.json', after)
        if after != before:
            raise ValueError('Frozen workspace parents changed')
        write(OUT/f'execution_{args.task}.json', dict(exit_code=code, task=args.task, command=command,
              snapshot=str(workspace), frozen_workspace_files_unchanged=len(before), legacy_files_verified=count))
    raise SystemExit(code)


if __name__ == '__main__':
    main()
