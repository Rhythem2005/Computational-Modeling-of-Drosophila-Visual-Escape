"""Explicit reviewed room protocol only; no automatic preview or experiment startup."""
import argparse,fcntl,json,os,subprocess,sys,time
from pathlib import Path
from ..avoidance.contracts import digest
from ..avoidance.recording import atomic_json
from .contracts import load_protocol,MODELS
from .execution import ROOT,durable_snapshot,protected_fingerprints,unattempted_jobs

def approval(protocol,path):
    a=json.loads(Path(path).read_text())
    if a.get('status')!='APPROVED_EXACT_ROOM_PROTOCOL' or a.get('protocol_sha256')!=digest(protocol) or a.get('episode_cap')!=24 or a.get('training_authorized') is not False or a.get('held_out_authorized') is not False:raise ValueError('Exact room protocol review missing or changed')
    return a

def worker(args):
    from .runner import RoomRunner
    from .recording import save
    from .neural_adapter import NullDiagnostic,FrontCircuitDiagnostic
    record,c,scenes=load_protocol(args.protocol);out=Path(args.output).resolve()
    if not out.is_relative_to(ROOT/'dashboard/runs'):raise ValueError('Worker output outside dashboard')
    approval(args.protocol,out/'authorization.json');ledger=json.loads((ROOT/'dashboard/.runtime/room_budgets'/(digest(args.protocol)+'.json')).read_text());job=json.loads(Path(args.job).read_text())
    if ledger['attempts'][-1]!={'job':job,'status':'RESERVED'} or job['model'] not in MODELS or '/' in job['id'] or '..' in job['id']:raise ValueError('No matching room reservation')
    scene=next(s for s in scenes if s.scenario_id==job['scene']);diagnostic=FrontCircuitDiagnostic(args.snapshot_record,c.motion.duration_ms) if record['neural_diagnostic'] else NullDiagnostic()
    observer=None;publisher=None;run=None
    try:
        if args.live:
            import base64,numpy as np
            sys.path.insert(0,str(ROOT/'dashboard/backend'))
            from fly_dashboard.producer import DashboardPublisher
            from fly_dashboard.repository import png_gray
            from ..avoidance.telemetry import AsyncObserver
            publisher=DashboardPublisher('http://127.0.0.1:8001',os.environ['FLY_DASHBOARD_INGEST_TOKEN'])
            config=c.public();config.update(room_scene=scene.public(),neural_role=diagnostic.role)
            publisher.open(name=job['id'],protocol=record['protocol_id'],controller=job['model'],source_note='Fresh room computation; artificial surround vision; declared color/size/map priors; neural activity diagnostic only',world_config=config)
            def send(value):
                value=dict(value);image=value.pop('camera_frame');stride=max(1,int(np.ceil(max(image.shape[:2])/512)));value['camera_png_base64']=base64.b64encode(png_gray(image[::stride,::stride])).decode()
                value['sensor_views']=[dict(id=v['id'],time_ms=v['time_ms'],quaternion_xyzw=v['quaternion_xyzw'],png_base64=base64.b64encode(png_gray(v['image'])).decode()) for v in value.pop('sensor_frames')]
                publisher.publish(value)
            observer=AsyncObserver(send)
        run=RoomRunner(c,job['model'],diagnostic).run(scene,observer,deadline=time.monotonic()+record['max_stage_seconds'])
        if observer:run['telemetry']=observer.close()
        run['execution_fingerprint']=dict(source_sha256={str(p.relative_to(ROOT)):digest(p) for p in Path(__file__).parent.glob('*.py')},python=sys.version,numpy=__import__('numpy').__version__,snapshot_record_sha256=digest(args.snapshot_record))
        save(out/'attempts'/job['id'],run,c,scene)
    except BaseException as e:
        import traceback
        atomic_json(out/(job['id']+'_failure.json'),dict(error=str(e),traceback=traceback.format_exc(),no_automatic_retry=True));raise
    finally:
        if observer and run is None:observer.close()
        if publisher:publisher.close()
        if not diagnostic.verify_preserved():raise ValueError('Historical snapshot changed')

def launch(args):
    record,c,scenes=load_protocol(args.protocol);a=approval(args.protocol,args.authorization)
    if type(record.get('neural_diagnostic')) is not bool:raise ValueError('Neural diagnostic choice must be reviewed')
    from .world import RoomWorld
    for scene in scenes:RoomWorld(c,scene)  # Initial geometry validation only; no steps.
    if record['neural_diagnostic'] and not any(v.id=='front' and v.width==256 and v.height==256 for v in c.views):raise ValueError('Reviewed front diagnostic camera missing')
    if args.live:
        from urllib.request import urlopen
        with urlopen('http://127.0.0.1:8001/api/v1/health',timeout=5) as r:health=json.load(r)
        if not health.get('surround_rgb') or not health.get('body_orientation') or not health.get('producer_ingestion') or not health.get('frontend_ready'):raise ValueError('Updated authenticated room backend/frontend required before reservations')
        if not os.environ.get('FLY_DASHBOARD_INGEST_TOKEN'):raise ValueError('Producer credential missing')
        from urllib.request import Request
        spec=dict(name='Room preflight (no session)',protocol=record['protocol_id'],controller='preflight',source_note='Schema/authentication validation only; no observations or simulation',world_config=c.public())
        request=Request('http://127.0.0.1:8001/api/v1/producer/check',data=json.dumps(spec).encode(),headers={'Content-Type':'application/json','X-Fly-Ingest-Token':os.environ['FLY_DASHBOARD_INGEST_TOKEN']},method='POST')
        with urlopen(request,timeout=5) as r:checked=json.load(r)
        if not checked['authenticated'] or not checked['schema_valid'] or checked['available_sessions']<1:raise ValueError('Producer preflight unavailable; no physical attempt reserved')
    continuation=getattr(args,'continue_record',None)
    out=Path(continuation).resolve() if continuation else ROOT/'dashboard/runs'/('room_'+str(time.time_ns()))
    if not out.is_relative_to(ROOT/'dashboard/runs') or (continuation and not out.is_dir()):raise ValueError('Invalid continuation directory')
    if not continuation:out.mkdir()
    budget=ROOT/'dashboard/.runtime/room_budgets'/(digest(args.protocol)+'.json')
    jobs=[dict(id=f'{i:02}_{s.scenario_id}_{model}',scene=s.scenario_id,model=model) for i,(s,model) in enumerate((s,m) for s in scenes for m in MODELS)]
    lockpath=ROOT/'connectome/Results/phase11/results/manual_worker.lock'
    with lockpath.open('r') as lease:
        fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
        ledger=None;start=None
        before=protected_fingerprints()
        suffix=('_continuation_'+str(time.time_ns())) if continuation else ''
        atomic_json(out/('preservation_before'+suffix+'.json'),before)
        try:
            if continuation:
                ledger=json.loads(budget.read_text())
                pending=unattempted_jobs(jobs,ledger,digest(args.protocol),out)
                if json.loads((out/'authorization.json').read_text())!=a:raise ValueError('Continuation approval differs')
                if not pending:raise RuntimeError('All room jobs already consumed; no retries')
            else:
                if budget.exists():raise RuntimeError('Room budget exists; explicit --continue-record required for untouched jobs only')
                pending=jobs
            snapshot=durable_snapshot(args.snapshot_record)
            atomic_json(out/('snapshot'+suffix+'.json'),json.loads(snapshot.read_text()))
            from connectome.scripts.phase11.runtime import sample,assess
            first=sample();time.sleep(2);second=sample();errors=assess(first,second,record['max_output_bytes'])
            atomic_json(out/('resource_preflight'+suffix+'.json'),dict(samples=[first,second],blockers=errors))
            if errors:
                atomic_json(out/('startup_status'+suffix+'.json'),dict(status='BLOCKED_BEFORE_ATTEMPT_RESERVATION',blockers=errors,new_reserved_attempts=0))
                raise RuntimeError('Resource preflight: '+','.join(errors))
            if not continuation:
                atomic_json(out/'protocol.json',record);atomic_json(out/'authorization.json',a)
                budget.parent.mkdir(parents=True,exist_ok=True)
                ledger=dict(protocol_sha256=digest(args.protocol),output=str(out),attempts=[],cap=24,elapsed_seconds=0.)
                atomic_json(budget,ledger)
            elapsed_before=ledger.get('elapsed_seconds',0.);start=time.monotonic()
            for job in pending:
                elapsed=elapsed_before+time.monotonic()-start
                if elapsed>=record['max_stage_seconds'] or sum(p.stat().st_size for p in out.rglob('*') if p.is_file())>=record['max_output_bytes']:raise RuntimeError('Room cumulative time/output limit')
                ledger['attempts'].append(dict(job=job,status='RESERVED'));ledger['elapsed_seconds']=elapsed
                atomic_json(budget,ledger);atomic_json(out/'current_job.json',job)
                env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',VECLIB_MAXIMUM_THREADS='1',MKL_NUM_THREADS='1')
                command=[str(ROOT/'venv/bin/python'),'-B','-m','dashboard.simulation.room_flight.launch','--worker','--protocol',str(Path(args.protocol).resolve()),'--snapshot-record',str(snapshot),'--job',str(out/'current_job.json'),'--output',str(out)]+(['--live'] if args.live else [])
                try:
                    with (out/(job['id']+'.log')).open('x') as log:result=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=record['max_stage_seconds']-elapsed)
                except BaseException as e:
                    ledger['attempts'][-1].update(status='INTERRUPTED' if isinstance(e,KeyboardInterrupt) else 'FAILED',error=type(e).__name__+': '+str(e));raise
                else:
                    ledger['attempts'][-1]['status']='COMPLETE' if result.returncode==0 else 'FAILED'
                finally:
                    ledger['elapsed_seconds']=elapsed_before+time.monotonic()-start;atomic_json(budget,ledger)
                if result.returncode:raise RuntimeError('Room attempt failed; no automatic retry: '+job['id'])
            from .recording import adjudicate
            records=[json.loads((out/'attempts'/j['job']['id']/'verified.json').read_text()) for j in ledger['attempts'] if j['status']=='COMPLETE']
            atomic_json(out/('summary'+suffix+'.json'),dict(status='RECORDED_ROOM_DEVELOPMENT_NOT_GENERALIZATION',attempts=len(ledger['attempts']),completed=len(records),attempt_history=ledger['attempts'],adjudication=adjudicate(records),training_runs=0,held_out_evaluations=0))
        finally:
            if start is not None:
                ledger['elapsed_seconds']=elapsed_before+time.monotonic()-start;atomic_json(budget,ledger)
            preserved=before==protected_fingerprints();atomic_json(out/('preservation'+suffix+'.json'),dict(scientific_sources_and_checkpoint_pointers_unchanged=preserved))
            if not preserved:raise RuntimeError('Protected scientific state changed')
    print(out)

def main():
    p=argparse.ArgumentParser();p.add_argument('--protocol',required=True);p.add_argument('--authorization');p.add_argument('--snapshot-record',required=True);p.add_argument('--live',action='store_true');p.add_argument('--worker',action='store_true');p.add_argument('--job');p.add_argument('--output');p.add_argument('--continue-record',help='Explicitly continue only untouched jobs in this room run; consumed attempts are never retried');args=p.parse_args()
    if args.worker:worker(args)
    else:
        if not args.authorization:raise ValueError('Exact room protocol approval required')
        launch(args)
if __name__=='__main__':main()
