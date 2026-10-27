"""Explicitly approved protocol only. Never starts from a template or on backend startup."""
import argparse,json,os,sys,time,subprocess,fcntl,hashlib
from pathlib import Path
from .contracts import load_protocol,verify_authorization,digest,MODELS
from .recording import atomic_json
ROOT=Path(__file__).resolve().parents[3]

def worker(protocol,job_path,output,snapshot_record,live):
    from .circuit import FrozenCircuit
    from .runner import Runner
    from .recording import save_attempt
    from .telemetry import AsyncObserver
    record,c,scenarios=load_protocol(protocol);job=json.loads(Path(job_path).read_text())
    scenario=next(s for s in scenarios if s.scenario_id==job['scenario_id'])
    circuit=FrozenCircuit(snapshot_record,c.duration_ms);observer=None;publisher=None
    if live:
        import base64
        sys.path.insert(0,str(ROOT/'dashboard/backend'))
        from fly_dashboard.producer import DashboardPublisher
        from fly_dashboard.repository import png_gray
        publisher=DashboardPublisher('http://127.0.0.1:8001',os.environ['FLY_DASHBOARD_INGEST_TOKEN'])
        publisher.open(name=job['id'],protocol=record['protocol_id'],controller=job['model'],source_note='Fresh multi-object computation; separate engineering controller; known common size prior',world_config=c.public())
        def send(packet):
            packet=dict(packet);packet['camera_png_base64']=base64.b64encode(png_gray(packet.pop('camera_frame'))).decode()
            publisher.publish(packet)
        observer=AsyncObserver(send)
    run=None
    try:
        run=Runner(c,job['model'],circuit).run(scenario,observer,deadline=time.monotonic()+record['max_stage_seconds'])
        if observer:run['telemetry']=observer.close()
        run['execution_fingerprint']=dict(observer_sources={str(p.relative_to(ROOT)):digest(p) for p in Path(__file__).parent.glob('*.py')},python=sys.version,numpy=__import__('numpy').__version__,snapshot_record_sha256=digest(snapshot_record))
        save_attempt(Path(output)/'attempts'/job['id'],run,c,scenario)
    except BaseException as e:
        import traceback
        atomic_json(Path(output)/(job['id']+'_failure.json'),dict(error=str(e),type=type(e).__name__,traceback=traceback.format_exc(),no_automatic_retry=True))
        raise
    finally:
        if observer and run is None:observer.close()
        if publisher:publisher.close()
        if not circuit.verify_preserved():raise RuntimeError('Historical scientific snapshot changed')

def launch(args):
    protocol=Path(args.protocol).resolve();record,c,scenarios=load_protocol(protocol)
    approval=verify_authorization(protocol,args.authorization)
    parent=ROOT/'connectome/Results/collision_threat_v2/runs/1793096608346990000/manifest.json'
    frozen=json.loads(parent.read_text())['world_config']
    for name in ('fly_radius','camera_width','camera_height','camera_fps','camera_center_px','camera_focal_px','camera_near_depth','background_uint8','object_uint8','actuation_delay_ms','escape_speed_max','escape_acceleration_max','success_final_clearance_min'):
        actual=getattr(c,name)
        if isinstance(actual,tuple):actual=list(actual)
        if actual!=frozen[name]:raise ValueError('Frozen baseline parameter changed: '+name)
    if record.get('frozen_parent_manifest_sha256')!=digest(parent):raise ValueError('Parent study identity changed')
    if args.live and not os.environ.get('FLY_DASHBOARD_INGEST_TOKEN'):raise ValueError('Live producer token missing')
    continuing=bool(args.continue_unattempted)
    output=Path(args.continue_unattempted).resolve() if continuing else ROOT/'dashboard/runs'/('multi_'+str(time.time_ns()))
    if continuing:
        if not output.is_relative_to(ROOT/'dashboard/runs') or digest(output/'protocol.json')!=digest(protocol):raise ValueError('Continuation protocol/output mismatch')
        if json.loads((output/'authorization.json').read_text())!=approval:raise ValueError('Continuation authorization differs')
    else:output.mkdir()
    snapshot=json.loads(Path(args.snapshot_record).read_text())
    for name,h in snapshot['files_sha256'].items():
        if digest(Path(snapshot['path'])/name)!=h:raise ValueError('Snapshot preflight mismatch: '+name)
    atomic_json(output/('continuation_snapshot_'+str(time.time_ns())+'.json' if continuing else 'execution_snapshot.json'),snapshot)
    print('OUTPUT '+str(output),flush=True)
    pointers=[ROOT/'connectome/Results/phase11/results/job_ledger.json',ROOT/'connectome/Results/phase11/results/training/train_55011_55102_0p001/current.json']
    current=json.loads(pointers[-1].read_text());pointers.append(pointers[-1].parent/current['arrays_file'])
    sources=list((ROOT/'connectome/scripts').rglob('*.py'));protected=pointers+sources
    before={str(p.relative_to(ROOT)):digest(p) for p in protected}
    if not continuing:
        atomic_json(output/'preservation_before.json',before);atomic_json(output/'protocol.json',record);atomic_json(output/'authorization.json',approval)
    # A reviewed protocol can consume its bounded stage exactly once; failed reservations remain.
    budget_root=ROOT/'dashboard/.runtime/protocol_budgets';budget_root.mkdir(parents=True,exist_ok=True)
    budget=budget_root/(digest(protocol)+'.json')
    with (ROOT/'connectome/Results/phase11/results/manual_worker.lock').open('r') as lease:
        fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if budget.exists() and not continuing:raise RuntimeError('This exact protocol already reserved attempts; no automatic rerun')
        if continuing and not budget.exists():raise RuntimeError('Continuation needs an existing attempt ledger')
        from connectome.scripts.phase11.runtime import sample,assess
        first=sample();time.sleep(2);second=sample();blockers=assess(first,second,record['max_output_bytes'])
        atomic_json(output/('resource_preflight_continuation_'+str(time.time_ns())+'.json' if continuing else 'resource_preflight.json'),dict(samples=[first,second],blockers=blockers))
        if blockers:raise RuntimeError('Resource preflight: '+','.join(blockers))
        jobs=[dict(id=f'{i:02}_{s.scenario_id}_{model}',scenario_id=s.scenario_id,model=model) for i,(s,model) in enumerate((s,m) for s in scenarios for m in MODELS)]
        ledger=json.loads(budget.read_text()) if continuing else dict(protocol_sha256=digest(protocol),cap=24,attempts=[])
        if ledger['protocol_sha256']!=digest(protocol):raise ValueError('Ledger protocol mismatch')
        reserved={a['job']['id'] for a in ledger['attempts']}
        jobs=[job for job in jobs if job['id'] not in reserved]
        if not jobs:raise RuntimeError('No unattempted jobs; failed/reserved attempts cannot be retried')
        ledger.setdefault('started_at', (output/'preservation_before.json').stat().st_mtime)
        atomic_json(budget,ledger)
        allowed_seconds=max(0,record['max_stage_seconds']-(time.time()-ledger['started_at']))
        started=time.monotonic()
        try:
            for job in jobs:
                if time.monotonic()-started>=allowed_seconds:raise TimeoutError('Stage budget exhausted')
                if sum(p.stat().st_size for p in output.rglob('*') if p.is_file())>=record['max_output_bytes']:raise RuntimeError('Output cap reached')
                ledger['attempts'].append(dict(job=job,status='RESERVED'));atomic_json(budget,ledger)
                print('RUN '+job['id'],flush=True)
                job_path=output/'current_job.json';atomic_json(job_path,job)
                env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',VECLIB_MAXIMUM_THREADS='1',MKL_NUM_THREADS='1')
                command=[str(ROOT/'venv/bin/python'),'-B','-m','dashboard.simulation.avoidance.cli','--worker','--protocol',str(protocol),'--job',str(job_path),'--output',str(output),'--snapshot-record',str(Path(args.snapshot_record).resolve())]+(['--live'] if args.live else [])
                with (output/(job['id']+'.log')).open('w') as log:
                    result=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=max(1,allowed_seconds-(time.monotonic()-started)))
                ledger['attempts'][-1]['status']='COMPLETE' if result.returncode==0 else 'FAILED';atomic_json(budget,ledger)
                if result.returncode:raise RuntimeError('Attempt failed; evidence retained: '+job['id'])
                print('DONE '+job['id'],flush=True)
            results=[]
            for entry in ledger['attempts']:
                if entry['status']!='COMPLETE':continue
                job=entry['job']
                verified=json.loads((output/'attempts'/job['id']/'verified.json').read_text())
                results.append(dict(job=job,metrics=verified['metrics']))
            atomic_json(output/'summary.json',dict(status='COMPLETED_EXECUTION_OUTCOMES_RECORDED',acceptance_status='REQUIRES_PREREGISTERED_OUTCOME_REVIEW',attempts=len(ledger['attempts']),completed=len(results),failed=[a['job']['id'] for a in ledger['attempts'] if a['status']!='COMPLETE'],results=results,training_runs=0,held_out_evaluations=0))
        finally:
            after={str(p.relative_to(ROOT)):digest(p) for p in protected};atomic_json(output/'preservation.json',dict(scientific_sources_and_pointers_unchanged=before==after))
            if before!=after:raise RuntimeError('Protected scientific files changed')
    print(output)

def main():
    p=argparse.ArgumentParser();p.add_argument('--protocol',required=True);p.add_argument('--authorization');p.add_argument('--snapshot-record',required=True);p.add_argument('--live',action='store_true');p.add_argument('--worker',action='store_true');p.add_argument('--job');p.add_argument('--output');p.add_argument('--continue-unattempted');args=p.parse_args()
    if args.worker:
        if not args.job or not args.output:raise ValueError('Worker needs a pre-reserved job')
        # Worker must also bind the exact approved protocol through its parent's copied authorization.
        output=Path(args.output).resolve()
        if not output.is_relative_to(ROOT/'dashboard/runs'):raise ValueError('Worker output outside dashboard runs')
        verify_authorization(args.protocol,output/'authorization.json')
        ledger_path=ROOT/'dashboard/.runtime/protocol_budgets'/(digest(args.protocol)+'.json')
        ledger=json.loads(ledger_path.read_text());job=json.loads(Path(args.job).read_text())
        if not ledger['attempts'] or ledger['attempts'][-1]!={'job':job,'status':'RESERVED'}:raise ValueError('No matching reserved attempt')
        if Path(args.job).resolve()!=output/'current_job.json' or job['model'] not in MODELS or '/' in job['id'] or '..' in job['id']:raise ValueError('Invalid reserved job')
        worker(args.protocol,args.job,args.output,args.snapshot_record,args.live)
    else:
        if not args.authorization:raise ValueError('Exact protocol authorization required')
        launch(args)
if __name__=='__main__':main()
