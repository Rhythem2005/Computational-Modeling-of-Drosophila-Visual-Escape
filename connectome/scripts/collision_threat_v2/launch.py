"""One v2 comparison, preserving fixed scientific paths while dashboard work continues."""
import fcntl
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
from .common import ROOT,BASE,PLAN,V1,REFERENCE,read,sha,write,sources,protected_names,inventory,size,verify_plan

def snapshot():
    from connectome.scripts.collision_threat_v1.launch_prototype import prepare_snapshot
    workspace,copied=prepare_snapshot()
    def copy(p):
        name=str(p.relative_to(ROOT));target=workspace/name
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target);copied[name]=sha(p)
    for p in Path(__file__).parent.rglob('*'):
        if p.is_file() and not {'__pycache__','.pytest_cache'}.intersection(p.parts):copy(p)
    for p in PLAN.iterdir():
        if p.is_file():copy(p)
    copy(BASE/'authorization.json');copy(V1/'prototype/attempt_ledger.json')
    proof=read(PLAN/'evidence_snapshot.json')
    for name in {**proof['evidence_sha256'],**proof['production_pointers_sha256']}:
        p=ROOT/name;copy(p)
        if name.endswith('/current.json'):copy(p.parent/read(p)['arrays_file'])
    aliases=('no_action','circuit','closest_approach_rule','circuit_threat_gate')
    for s in read(PLAN/'proposed_protocol.json')['scenarios']:
        for alias in aliases:
            for suffix in ('.json','.npz'):copy(REFERENCE/'episodes'/f"{s['scenario_id']}_{alias}_r0{suffix}")
    return workspace,copied

def main():
    proposal=verify_plan()
    authorization=read(BASE/'authorization.json')
    if (authorization['status']!='USER_APPROVED_IMPLEMENTATION'
            or authorization['plan_sha256']!=sha(PLAN/'README.md')
            or authorization['proposed_protocol_sha256']!=sha(PLAN/'proposed_protocol.json')):
        raise ValueError('Missing approved v2 implementation scope')
    output=BASE/'runs'/str(time.time_ns());output.mkdir(parents=True,exist_ok=False)
    names=protected_names();before=inventory(names);initial_sources=sources()
    write(output/'preservation_before.json',before)
    write(output/'authorization.json',authorization)
    write(output/'preservation_scope.json',dict(scope='Fixed earlier scientific filenames plus v1 evidence and approved plan',
         dashboard_files_enumerated=False,root_project_readme_enumerated=False,
         unrelated_added_files_ignored=True,protected_filename_count=len(names)))
    code=None
    try:
        with (ROOT/'connectome/Results/phase11/results/manual_worker.lock').open('r') as lease:
            fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
            ledger_path=BASE/'runs/attempt_ledger.json';approval_sha=sha(BASE/'authorization.json')
            if ledger_path.exists():
                ledger=read(ledger_path)
                if ledger['attempts']:raise RuntimeError('v2 attempts already consumed; no automatic extra runs/retries')
                if ledger['authorization_sha256']!=approval_sha:raise ValueError('Attempt ledger approval changed')
            else:write(ledger_path,dict(authorization_sha256=approval_sha,approved_cap=80,attempts=[]))
            from connectome.scripts.phase11.runtime import sample,assess
            first=sample();time.sleep(2);second=sample();errors=assess(first,second,1024**3)
            write(output/'resource_preflight.json',dict(samples=[first,second],blockers=errors,
                  disk_estimate_advisory=True,disk_warning=second['disk_free_bytes']<1024**3))
            if errors:raise RuntimeError('Resource startup gate: '+', '.join(errors))
            workspace,copied=snapshot()
            write(output/'snapshot.json',dict(path=str(workspace),files_sha256=copied,bytes=size(workspace)))
            if size(workspace)+size(output)>1024**3:raise RuntimeError('Snapshot/output budget exceeded')
            env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',
                     VECLIB_MAXIMUM_THREADS='1',MKL_NUM_THREADS='1',FLY_V2_SNAPSHOT='1',
                     FLY_V2_OUTPUT=str(output),FLY_V2_LEDGER=str(ledger_path))
            command=[sys.executable,'-B','-m','connectome.scripts.collision_threat_v2.run']
            print(f'v2 output: {output}\nVerified snapshot: {workspace}',flush=True)
            with (output/'execution.log').open('w') as log:
                worker=subprocess.Popen(command,cwd=workspace,env=env,stdout=log,stderr=subprocess.STDOUT)
                try:code=worker.wait(timeout=45*60)
                finally:
                    if worker.poll() is None:
                        worker.terminate()
                        try:worker.wait(timeout=5)
                        except subprocess.TimeoutExpired:worker.kill();worker.wait()
            for name,h in copied.items():
                if sha(workspace/name)!=h:raise RuntimeError(f'Execution dependency/source changed: {name}')
            write(output/'execution.json',dict(exit_code=code,command=command,snapshot=str(workspace),
                  copied_files_unchanged=True,snapshot_bytes=size(workspace)))
            fcntl.flock(lease,fcntl.LOCK_UN)
    except BaseException as error:
        write(output/'launcher_failure.json',dict(error=str(error),type=type(error).__name__,traceback=traceback.format_exc()))
        raise
    finally:
        after=inventory(names);write(output/'preservation_after.json',after)
        unchanged=before==after;same_sources=initial_sources==sources()
        write(output/'preservation.json',dict(unchanged=unchanged,files=len(names),active_sources_unchanged=same_sources,
             dashboard_work_excluded=True,v1_ledger_consumed=len(read(V1/'prototype/attempt_ledger.json')['attempts'])))
        if not unchanged or not same_sources:raise RuntimeError('Scientific artifacts or active source changed')
    raise SystemExit(code)

if __name__=='__main__':main()
