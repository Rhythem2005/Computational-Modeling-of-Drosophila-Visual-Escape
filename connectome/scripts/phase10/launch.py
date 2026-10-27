"""Compatibility execution copy for renamed, hash-frozen earlier phases."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from .common import ROOT, BASE, OUT, sha, write_json


def protected():
    paths = [p for base in (ROOT/'connectome/Results', ROOT/'connectome/scripts') for p in base.rglob('*')
             if p.is_file() and 'phase10' not in p.relative_to(base).parts and not {'__pycache__','.pytest_cache'}.intersection(p.parts)]
    paths += [ROOT/n for n in ('README.md','config.yaml','requirements.txt','STUDY_CHECKPOINT.md') if (ROOT/n).exists()]
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(paths)}


def legacy_source(name):
    if name.startswith('connectome/phase'):
        return ROOT / name.replace('connectome/phase', 'connectome/Results/phase', 1)
    if name.startswith('connectome/data/phase1/'):
        return ROOT / name.replace('connectome/data/phase1/', 'connectome/Results/phase1/', 1)
    return ROOT/name


def snapshot():
    before = protected()
    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT/'workspace_before.json', before, immutable=True)
    # The saved execution inventory defines the precise legacy namespace, not
    # guessed directory aliases or silently edited frozen source/lock files.
    expected = json.loads((ROOT/'connectome/Results/phase9/results/preservation_before.json').read_text())
    expected.update(json.loads((ROOT/'connectome/Results/phase9/results/delivery_artifact_index.json').read_text()))
    lock = json.loads((ROOT/'connectome/Results/phase9/results/definition_lock.json').read_text())
    expected.update(lock['sources_sha256'])
    expected['connectome/phase9/results/definition_lock.json'] = sha(ROOT/'connectome/Results/phase9/results/definition_lock.json')
    # Include the index itself and any parent files not inventoried as outputs.
    expected['connectome/phase9/results/delivery_artifact_index.json'] = sha(ROOT/'connectome/Results/phase9/results/delivery_artifact_index.json')
    copy = Path(tempfile.mkdtemp(prefix='fly-phase10-execution-'))
    translated = []
    for name, value in expected.items():
        source = ROOT/'connectome/Results/phase9/execution_baseline/README.md' if name == 'README.md' else legacy_source(name)
        if not source.is_file() or sha(source) != value:
            raise ValueError(f'Frozen parent mismatch after explicit path translation: {name}')
        target = copy/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        if str(source.relative_to(ROOT)) != name:
            translated.append([str(source.relative_to(ROOT)), name])
    for base in (BASE, ROOT/'connectome/scripts/phase10'):
        for source in base.rglob('*'):
            if source.is_file() and '__pycache__' not in source.parts:
                target = copy/source.relative_to(ROOT)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
    return copy, before, dict(parent_files_checked=len(expected), namespace_translations=translated,
                              original_readme_sha256=before['README.md'], archival_readme_sha256=expected['README.md'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--task', choices=['preflight','validate'], default='validate')
    args = parser.parse_args()
    copy, before, evidence = snapshot()
    command = [sys.executable, '-m', 'connectome.scripts.phase10.validate', '--task', args.task]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', MPLCONFIGDIR='/tmp/fly-phase10-mpl',
               OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', VECLIB_MAXIMUM_THREADS='1')
    print('Phase 10 isolated execution:', copy, flush=True)
    try:
        result = subprocess.run(command, cwd=copy, env=env)
        outputs = copy/'connectome/Results/phase10/results'
        if outputs.exists():
            shutil.copytree(outputs, OUT, dirs_exist_ok=True)
    finally:
        after = protected()
        write_json(OUT/'workspace_after.json', after)
        if before != after:
            raise ValueError('Earlier workspace files changed')
    write_json(OUT/'execution.json', dict(snapshot=str(copy), command=command, exit_code=result.returncode,
                                          parent_files_unchanged=len(before), **evidence))
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
