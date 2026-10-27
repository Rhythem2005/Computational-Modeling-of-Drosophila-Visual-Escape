"""Authorized <=60-attempt prototype in a byte-verified historical namespace."""
import fcntl
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
from .common import ROOT,BASE,SOURCE_RUN,read,sha,sources,inventory,size
from .protocol import authorization
from .prototype_io import write

def old_stage_a_files():
    folder=BASE/'1793092658671112000'
    return {str(p.relative_to(ROOT)):sha(p) for p in folder.rglob('*') if p.is_file()}

def prepare_snapshot():
    from connectome.scripts.behavior_validation.launch import snapshot
    workspace,copied=snapshot()
    def copy(source):
        name=str(source.relative_to(ROOT));target=workspace/name
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target);copied[name]=sha(source)
    for source in Path(__file__).parent.rglob('*'):
        if source.is_file() and not {'__pycache__','.pytest_cache'}.intersection(source.parts):copy(source)
    for name in ('decision_rule_spec.md','candidate_manifest.json','candidate_authorization.json',
                 '1793092658671112000/information_audit.json'):
        copy(BASE/name)
    old=read(SOURCE_RUN/'manifest.json')
    for job in old['jobs']:
        if job['repeat']==0 and job['mapping']=='uniform_population' and job['model_id'] in ('circuit','feature_only','no_action'):
            for suffix in ('.npz','.json'):copy(SOURCE_RUN/'episodes'/(job['episode_id']+suffix))
    return workspace,copied

def main():
    authorization()
    output=BASE/'prototype'/str(time.time_ns());output.mkdir(parents=True,exist_ok=False)
    before=inventory();stage_a_before=old_stage_a_files();source_before=sources()
    write(output/'preservation_before.json',before)
    write(output/'stage_a_preservation_before.json',stage_a_before)
    write(output/'authorization.json',read(BASE/'candidate_authorization.json'))
    code=None
    try:
        with (ROOT/'connectome/Results/phase11/results/manual_worker.lock').open('r') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            ledger_path=BASE/'prototype/attempt_ledger.json'
            approval_sha=sha(BASE/'candidate_authorization.json')
            if ledger_path.exists():
                ledger=read(ledger_path)
                if ledger['attempts']:
                    raise RuntimeError('Approved prototype has already consumed attempts; no automatic extra run or retry')
                if ledger['authorization_sha256']!=approval_sha:raise ValueError('Budget ledger approval changed')
            else:write(ledger_path,dict(authorization_sha256=approval_sha,approved_total_cap=60,attempts=[]))
            from connectome.scripts.phase11.runtime import sample,assess
            first=sample();time.sleep(2);second=sample();errors=assess(first,second,1024**3)
            write(output/'resource_preflight.json',dict(samples=[first,second],blockers=errors,
                  disk_estimate_advisory=True,disk_warning=second['disk_free_bytes']<1024**3))
            if errors:raise RuntimeError('Resource startup gate: '+', '.join(errors))
            workspace,copied=prepare_snapshot()
            write(output/'snapshot.json',dict(path=str(workspace),files_sha256=copied,bytes=size(workspace)))
            if size(workspace)+size(output)>1024**3:raise RuntimeError('Snapshot/output budget exceeded')
            env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',
                     VECLIB_MAXIMUM_THREADS='1',MKL_NUM_THREADS='1',FLY_COLLISION_SNAPSHOT='1',
                     FLY_COLLISION_OUTPUT=str(output),FLY_COLLISION_BUDGET_LEDGER=str(ledger_path))
            command=[sys.executable,'-B','-m','connectome.scripts.collision_threat_v1.prototype']
            print(f'Prototype output: {output}\nVerified snapshot: {workspace}',flush=True)
            with (output/'execution.log').open('w') as log:
                process=subprocess.Popen(command,cwd=workspace,env=env,stdout=log,stderr=subprocess.STDOUT)
                try:code=process.wait(timeout=45*60)
                finally:
                    if process.poll() is None:
                        process.terminate()
                        try:process.wait(timeout=5)
                        except subprocess.TimeoutExpired:process.kill();process.wait()
            for name,h in copied.items():
                if sha(workspace/name)!=h:raise RuntimeError(f'Copied source/dependency changed: {name}')
            write(output/'execution.json',dict(exit_code=code,snapshot=str(workspace),command=command,
                  copied_files_unchanged=True,snapshot_bytes=size(workspace)))
            fcntl.flock(lock,fcntl.LOCK_UN)
    except BaseException as error:
        write(output/'launcher_failure.json',dict(type=type(error).__name__,error=str(error),traceback=traceback.format_exc()))
        raise
    finally:
        after=inventory();stage_a_after=old_stage_a_files()
        write(output/'preservation_after.json',after)
        write(output/'stage_a_preservation_after.json',stage_a_after)
        preserved=before==after and stage_a_before==stage_a_after and source_before==sources()
        write(output/'preservation.json',dict(unchanged=before==after,files=len(before),
              stage_a_unchanged=stage_a_before==stage_a_after,stage_a_files=len(stage_a_before),
              active_sources_unchanged=source_before==sources()))
        if not preserved:raise RuntimeError('Protected original files, Stage A evidence, or active sources changed')
    raise SystemExit(code)

if __name__=='__main__':main()
