"""Reconstruct Phase 10's byte-verified legacy namespace without writing parents."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import signal
import time
import uuid
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


def publish_checkpoint(pointer,target_dir):
    """Copy one committed generation; source may advance during publication."""
    # Capture one committed pointer; never chase a moving generation mid-copy.
    raw = pointer.read_bytes()
    import json
    record = json.loads(raw)
    payload = pointer.parent/record['arrays_file']
    try:
        data = payload.read_bytes()
    except FileNotFoundError:
        return False  # Writer advanced two generations; retry next publication.
    import hashlib
    if hashlib.sha256(data).hexdigest() != record['arrays_sha256']:
        raise ValueError('Checkpoint publication hash mismatch')
    if not (target_dir/payload.name).exists() or (target_dir/payload.name).read_bytes()!=data:
        atomic(target_dir/payload.name, data)
    if not (target_dir/pointer.name).exists() or (target_dir/pointer.name).read_bytes()!=raw:
        atomic(target_dir/pointer.name, raw)
    for old in target_dir.glob('state_*.npz'):
        if int(old.stem.split('_')[1]) < record['generation']-1:
            old.unlink()
    return True


def publish(source, destination):
    """Commit arrays/pointers and completed reports before ledger publication."""
    source, destination = Path(source), Path(destination)
    # Capture registration state BEFORE scanning artifacts. A later ledger may
    # refer to reports created after their directories were already traversed.
    ledger_data=(source/'job_ledger.json').read_bytes() if (source/'job_ledger.json').exists() else None
    pointers = list(source.rglob('current.json'))
    checkpoint_dirs = {p.parent for p in pointers}
    for pointer in pointers:
        publish_checkpoint(pointer,destination/pointer.parent.relative_to(source))
    for p in source.rglob('*'):
        if not p.is_file() or p.name in ('current.json','job_ledger.json') or (p.parent in checkpoint_dirs and p.name.startswith('state_')):
            continue
        target = destination/p.relative_to(source)
        if p.name=='report.json' and (p.parent/'current.json').exists():
            # A trial can finish after the initial pointer pass. Refresh its
            # final generation before exposing the completion report.
            if not publish_checkpoint(p.parent/'current.json',target.parent):
                raise ValueError('Completed trial checkpoint moved during publication')
            selected=p.parent/'selected.npz'
            if selected.exists() and (not (target.parent/selected.name).exists() or sha(selected)!=sha(target.parent/selected.name)):
                atomic(target.parent/selected.name,selected.read_bytes())
        if not target.exists() or sha(p) != sha(target):
            atomic(target, p.read_bytes())
    if ledger_data is not None:
        data=ledger_data
        if not (destination/'job_ledger.json').exists() or (destination/'job_ledger.json').read_bytes()!=data:
            atomic(destination/'job_ledger.json',data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--task', choices=['integrity','engineering','preflight','profile','primary','secondary','freeze','continuous'], required=True)
    args = parser.parse_args()
    from .manual_stop import handlers
    from .runtime import lease
    with handlers(), lease():
        run(args)


def run(args):
    before = protected()
    write(OUT/'preservation_before.json', before, immutable=True)
    workspace, count = snapshot()
    command = [sys.executable, '-m', 'connectome.scripts.phase11.runner', '--task', args.task]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', MPLCONFIGDIR='/tmp/fly-phase11-mpl',
               OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', VECLIB_MAXIMUM_THREADS='1',
               FLY_PHASE11_LAUNCHER_PID=str(os.getpid()),FLY_PHASE11_INVOCATION=uuid.uuid4().hex)
    write(OUT/'execution_current.json', dict(task=args.task, snapshot=str(workspace), command=command,
          legacy_files_verified=count, sources_sha256=sources()))
    print(f'Phase 11 {args.task}: isolated workspace {workspace}', flush=True)
    code = None
    process = None
    forwarded = False
    last_publication = time.monotonic()
    try:
        process = subprocess.Popen(command, cwd=workspace, env=env,start_new_session=True)
        # Publish atomic checkpoint generations incrementally, including on failure.
        while True:
            try:
                code = process.wait(timeout=.2)
            except subprocess.TimeoutExpired:
                pass
            from . import manual_stop
            ready=workspace/'connectome/Results/phase11/results/worker_ready.json'
            if manual_stop.requested and not forwarded and ready.exists():
                record=read(ready)
                if record.get('invocation')==env['FLY_PHASE11_INVOCATION'] and code is None:
                    process.send_signal(signal.SIGINT)
                    forwarded=True
            if time.monotonic()-last_publication>=30:
                publish(workspace/'connectome/Results/phase11/results', OUT)
                last_publication=time.monotonic()
            if code is not None:
                break
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill();process.wait()
        outputs=workspace/'connectome/Results/phase11/results'
        if outputs.exists():publish(outputs,OUT)
        after = protected()
        write(OUT/'preservation_after.json', after)
        if after != before:
            raise ValueError('Frozen workspace parents changed')
        write(OUT/f'execution_{args.task}.json', dict(exit_code=code, task=args.task, command=command,
              snapshot=str(workspace), frozen_workspace_files_unchanged=len(before), legacy_files_verified=count,
              pause_requested=forwarded,final_publication_completed=True))
    if code==130:print('PAUSED: latest committed checkpoints published to Phase 11 results.',flush=True)
    raise SystemExit(code)


if __name__ == '__main__':
    main()
