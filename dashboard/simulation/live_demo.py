"""Bounded, read-only traced observation of the unchanged historical runners."""
import argparse, base64, fcntl, hashlib, json, os
from pathlib import Path
import struct, subprocess, sys, time, traceback, zlib
from urllib.request import Request, urlopen
ROOT=Path(__file__).resolve().parents[2]
REFERENCE=ROOT/'connectome/Results/collision_threat_v2/runs/1793096608346990000'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text())
def write(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n');os.replace(tmp,p)
def png(a):
    def chunk(k,v):return struct.pack('!I',len(v))+k+v+struct.pack('!I',zlib.crc32(k+v)&0xffffffff)
    h,w=a.shape
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!IIBBBBB',w,h,8,0,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(b'\0'+r.tobytes() for r in a),1))+chunk(b'IEND',b'')
class API:
    def __init__(self):self.token=os.environ['FLY_DASHBOARD_INGEST_TOKEN']
    def call(self,path,data=None,method='POST'):
        req=Request('http://127.0.0.1:8001/api/v1'+path,data=None if data is None else json.dumps(data,allow_nan=False).encode(),headers={'Content-Type':'application/json','X-Fly-Ingest-Token':self.token},method=method)
        with urlopen(req,timeout=5) as r:return json.load(r)
class Observer:
    def __init__(self,api,session,filename,np):
        self.api=api;self.session=session;self.filename=filename;self.np=np;self.start=time.monotonic();self.events=[];self.last=-1;self.moved=False;self.last_locals=None
        self.line=next(i for i,s in enumerate(Path(filename).read_text().splitlines(),1) if 'segment=world.step()' in s)
    def trace(self,frame,event,arg):
        if frame.f_code.co_filename!=self.filename or frame.f_code.co_name!='run':return None
        if event=='line' and frame.f_lineno==self.line:self.observe(frame.f_locals)
        return self.trace
    def observe(self,l,terminal=False):
        self.last_locals=l;w=l['world'];k=float(w.time_ms);out=l.get('out',{})
        if k<=self.last:return
        if not terminal:
            for key,kind,label in [('escape_event','request','Physical escape request'),('retirement_event','retirement','Candidate retired'),('rearm_event','rearm','Fresh threat re-armed')]:
                if out.get(key):self.events.append(dict(time_ms=k,kind=kind,label=label))
        if not self.moved and self.np.any(w.fly!=w.scenario['fly_position']):
            self.moved=True;self.events.append(dict(time_ms=k,kind='motion',label='First observed displacement'))
        if not terminal and k%10 and not self.events:return
        driver=l.get('driver');state=driver.state_vector() if driver else l['states'][-1]
        frames=l['frames'];times=l.get('times',l.get('frame_times'))
        camera_index=int(self.np.searchsorted(times,k/1000,side='right'))-1
        encoded=l.get('encoded');drive=l['drive'];ids=[int(v) for v in l['self'].pipeline.circuit.body_ids]
        event_list=self.events;self.events=[]
        if terminal and w.metrics().get('failure'):
            failure=w.metrics()['failure'];event_list.append(dict(time_ms=k,kind=failure['kind'],label=failure['kind'].title()))
        score=out.get('score',l.get('scores',[None])[-1])
        packet=dict(time_ms=k,fly=w.fly.tolist(),obstacles=[dict(id=o['id'],position=p.tolist(),radius=float(r)) for o,p,r in zip(w.scenario['obstacles'],w.obstacles,w.radii)],speed=float(w.speed),score=None if score is None else float(score),sustained_score=float(out['sustained_score']),gate_state=out.get('gate_state'),rule_state=out.get('rule_state'),encoder_channels=None if encoded is None else encoded.channels[-1].tolist(),encoder_drive=drive.tolist(),encoder_body_ids=ids,encoder_valid=None if encoded is None else bool(encoded.diagnostics['valid'][-1]),neural_kind='anatomical' if len(state)==321 else 'unavailable',neural_ids=ids if len(state)==321 else [],neural_values=state.tolist(),camera_timestamp_ms=float(times[camera_index]*1000),camera_png_base64=base64.b64encode(png(frames[camera_index])).decode(),events=event_list)
        # Pacing changes wall time only; no model input depends on wall time.
        time.sleep(max(0,self.start+k/100-time.monotonic()))
        self.api.call('/live/'+self.session+'/frames',packet);self.last=k

def worker(output,snapshot):
    import numpy as np, yaml
    from connectome.scripts.phase7.pipeline import FrozenPipeline
    from connectome.scripts.phase9.config import load_config,fixtures
    from connectome.scripts.phase9.runner import ClosedLoopRunner
    from connectome.scripts.collision_threat_v2.runner import Runner
    from connectome.scripts.collision_threat_v2.rule import KnownSizePrior
    from connectome.scripts.collision_threat_v1.features import camera_from_config
    from connectome.scripts.collision_threat_v1.protocol import legacy_rows
    from connectome.scripts.behavior_validation.evidence import verify_metrics
    api=API();config=load_config();pipeline=FrozenPipeline();scenarios=fixtures()
    manifest=read(REFERENCE/'manifest.json');assert config==manifest['world_config'] and scenarios==manifest['scenarios']
    camera=camera_from_config(config,yaml.safe_load((Path(snapshot)/'connectome/phase6/encoder_config.yaml').read_text()))
    prior=KnownSizePrior(manifest['size_information']['object_radius_prior'],manifest['size_information']['self_radius'])
    runner=Runner(pipeline,config,camera,legacy_rows(pipeline),prior)
    spatial=ClosedLoopRunner();jobs=[]
    for s in scenarios:jobs.append(dict(kind='v2',scenario=s['scenario_id'],model='finite_retirement_gate_v2',seed=None))
    for name in ('world_left','world_right'):
        for seed in config['spatial_seeds']:jobs.append(dict(kind='phase9',scenario=name,model='circuit',seed=seed))
    write(output/'manifest.json',dict(protocol='dashboard_live_known_fixture_v1',jobs=jobs,attempt_cap=15,simulation_rate=.1,source_snapshot=str(snapshot),reference_manifest_sha256=sha(REFERENCE/'manifest.json'),observer_sha256=sha(__file__),python=sys.version,numpy=np.__version__,scope='Engineering demonstration, not independent evaluation'))
    start_job=int(os.environ.get('FLY_DEMO_START_JOB','0'))
    results=[];sessions=[];begin=time.monotonic()
    for old in api.call('/live',method='GET')['sessions']:
        if old['protocol']=='dashboard_live_known_fixture_v1':
            if old['active']:api.call('/live/'+old['id']+'/end',{})
            api.call('/live/'+old['id'],method='DELETE')
    for i,job in enumerate(jobs):
        if i<start_job:continue
        if time.monotonic()-begin>600:raise RuntimeError('Ten-minute demonstration budget exhausted')
        if sum(p.stat().st_size for p in output.rglob('*') if p.is_file())>512*1024**2:raise RuntimeError('Output budget exhausted')
        ident=f"{i:02}_{job['scenario']}_{job['model']}"+(f"_s{job['seed']}" if job['seed'] is not None else '')
        write(output/'progress.json',dict(status='RUNNING',reserved_attempt=i+1,maximum=15,job=job,completed=results))
        # Each reset creates its own stream. Keep at most three ended/current sessions.
        if len(sessions)>=3:api.call('/live/'+sessions.pop(0),method='DELETE')
        session=api.call('/live',dict(name=ident,protocol='dashboard_live_known_fixture_v1',controller=job['model'],source_note=f"Fresh computation: {job['scenario']}; seed={job['seed']}; 0.1x wall pacing; frozen historical runner",world_config=config))['id'];sessions.append(session)
        write(output/'current_session.json',dict(id=session,job=job,url='http://127.0.0.1:8001/?live=follow'))
        target=runner if job['kind']=='v2' else spatial
        observer=Observer(api,session,target.run.__code__.co_filename,np)
        print(f"LIVE {i+1}/15 {ident} session={session}",flush=True)
        try:
            sys.settrace(observer.trace)
            s=next(s for s in scenarios if s['scenario_id']==job['scenario'])
            run=target.run(s,job['model']) if job['kind']=='v2' else target.run(s,condition=config['secondary_condition'],seed=job['seed'])
        finally:sys.settrace(None)
        observer.observe(observer.last_locals,terminal=True)
        metric_view=run if job['kind']=='v2' else dict(run,arrays=dict(run['arrays'],controller_states=run['arrays']['states']),metrics=dict(run['metrics'],model='circuit',frame_count=len(run['arrays']['frame_valid'])))
        verify_metrics(metric_view)
        if job['kind']=='v2':
            ref=REFERENCE/'episodes'/f"{job['scenario']}_{job['model']}_r0.npz"
            refmeta=read(ref.with_suffix('.json'));expected_metrics=refmeta['metrics']
        else:
            ref=ROOT/'connectome/Results/phase9/results/episodes'/f"{job['scenario']}_spatial_s{job['seed']}.npz"
            refmeta=read(ref.with_name(ref.stem+'_metadata.json'));expected_metrics=read(ref.with_name(ref.stem+'_metrics.json'))
        assert sha(ref)==refmeta['arrays_sha256']
        with np.load(ref,allow_pickle=False) as prior_arrays:
            for key,value in run['arrays'].items():np.testing.assert_array_equal(value,prior_arrays[key],err_msg=key)
        assert run['metrics']==expected_metrics,'Metrics differ from saved reference'
        path=output/'episodes'/f'{ident}.npz';path.parent.mkdir(exist_ok=True)
        np.savez_compressed(path,schema_version=np.array('collision_threat_2.0' if job['kind']=='v2' else '1.0'),**run['arrays'])
        meta={k:v for k,v in run.items() if k!='arrays'}
        meta.update(arrays_sha256=sha(path),model=job['model'],seed=job['seed'],mapping=config['secondary_condition'] if job['kind']=='phase9' else 'uniform_population',protocol='dashboard_live_known_fixture_v1',live_observer_reference_exact=True,reference=str(ref.relative_to(ROOT)),reference_sha256=sha(ref))
        write(path.with_suffix('.json'),meta)
        api.call('/live/'+session+'/end',{})
        results.append(dict(**job,metrics=run['metrics'],exact_reference_match=True,independent_metric_check=True))
        print(f"DONE {ident}: request={run['metrics']['first_request_ms']} success={run['metrics']['escape_success']} false_alarm={run['metrics']['false_alarm']}",flush=True)
    write(output/'summary.json',dict(status='COMPLETE',attempts=len(results),results=results,elapsed_s=time.monotonic()-begin,training_runs=0,held_out_evaluations=0))
    write(output/'progress.json',dict(status='COMPLETE',completed=len(results),maximum=15))

def launch():
    if (ROOT/'dashboard/runs/live_demo_20261027_summary.json').exists():
        raise RuntimeError('This bounded demonstration is closed; a new run requires its own authorized protocol.')
    output=ROOT/'dashboard/runs'/str(time.time_ns());output.mkdir(parents=True)
    record=read(REFERENCE/'snapshot.json');snapshot=Path(record['path'])
    for name,h in record['files_sha256'].items():
        if sha(snapshot/name)!=h:raise RuntimeError('Snapshot hash mismatch: '+name)
    protected=[ROOT/'connectome/Results/phase11/results/job_ledger.json',ROOT/'connectome/Results/phase11/results/training/train_55011_55102_0p001/current.json']
    protected+=list((ROOT/'connectome/scripts').rglob('*.py'))
    before={str(p.relative_to(ROOT)):sha(p) for p in protected}
    write(output/'preservation_before.json',before)
    with (ROOT/'connectome/Results/phase11/results/manual_worker.lock').open('r') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        from connectome.scripts.phase11.runtime import sample,assess
        first=sample();time.sleep(2);second=sample();errors=assess(first,second,512*1024**2)
        write(output/'resource_preflight.json',dict(samples=[first,second],blockers=errors))
        if errors:raise RuntimeError('Resource gate: '+', '.join(errors))
        write(output/'snapshot.json',record)
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',VECLIB_MAXIMUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONPATH=str(snapshot),FLY_BEHAVIOR_SNAPSHOT='1')
        command=[str(ROOT/'venv/bin/python'),'-B',str(Path(__file__).resolve()),'--worker',str(output),'--snapshot',str(snapshot)]
        print('OUTPUT '+str(output),flush=True)
        try:
            result=subprocess.run(command,cwd=snapshot,env=env,timeout=600)
            if result.returncode:raise RuntimeError('Worker failed: '+str(result.returncode))
        finally:
            same=all(sha(snapshot/n)==h for n,h in record['files_sha256'].items())
            after={str(p.relative_to(ROOT)):sha(p) for p in protected}
            write(output/'preservation.json',dict(production_sources_and_pointers_unchanged=before==after,snapshot_unchanged=same))
            if before!=after or not same:raise RuntimeError('Preservation check failed')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--worker');p.add_argument('--snapshot');args=p.parse_args()
    if args.worker:
        try:worker(Path(args.worker),args.snapshot)
        except BaseException as e:
            write(Path(args.worker)/'failure.json',dict(type=type(e).__name__,error=str(e),traceback=traceback.format_exc(),no_automatic_retry=True));raise
    else:
        sys.path.insert(0,str(ROOT));launch()
