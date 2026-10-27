"""Real SIGINT, process exit and fresh-process exact replay on synthetic fixtures."""
import os
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path
import numpy as np
import pytest
from connectome.scripts.phase11.common import ROOT,OUT,read,write,sha


def command(directory,point=None,early=False):
    result=[sys.executable,'-B','-m','connectome.scripts.phase11.tests.manual_fixture','--directory',str(directory)]
    if point:result+=['--pause',point]
    if early:result+=['--early']
    return result


@pytest.mark.parametrize('point,early',[('checkpoint_1',False),('checkpoint_3',False),
    ('before_registration',False),('between_trials',False),('checkpoint_3',True)])
def test_fresh_process_sigint_exact_continuation(point,early):
    base=OUT/'tests/manual'/uuid.uuid4().hex;a,b=base/'uninterrupted',base/'resumed'
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',VECLIB_MAXIMUM_THREADS='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
    baseline=subprocess.run(command(a,early=early),cwd=ROOT,env=env,capture_output=True,text=True,timeout=30)
    assert baseline.returncode==0,baseline.stderr
    process=subprocess.Popen(command(b,point,early),cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    deadline=time.monotonic()+20
    try:
        while not (b/'ready.json').exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(.01)
        assert (b/'ready.json').exists()
        process.send_signal(signal.SIGINT)
        _,err=process.communicate(timeout=15)
        assert process.returncode==130,err
    finally:
        if process.poll() is None:process.kill();process.wait()
    assert read(b/'paused.json')['status']=='PAUSED_CHECKPOINT_COMMITTED'
    resumed=subprocess.run(command(b,early=early),cwd=ROOT,env=env,capture_output=True,text=True,timeout=30)
    assert resumed.returncode==0,resumed.stderr
    ledgers=[read(p/'ledger.json') for p in (a,b)]
    assert [[(r['definition'],r['status']) for r in rows] for rows in ledgers][0]==[ (r['definition'],r['status']) for r in ledgers[1]]
    for directory in (a,b):
        complete=[e['job_id'] for e in read(directory/'events.json') if e['kind']=='COMPLETE']
        assert len(complete)==len(set(complete))==2
    for row in ledgers[0]:
        name=row['definition']['job_id'];left,right=a/'training'/name,b/'training'/name
        ca,cb=read(left/'current.json'),read(right/'current.json')
        for key in ('epoch','offset','order','rng_state','adam_updates','best_epoch','best_bce','stale','finished','history','train_sum','clipped','generation'):
            assert ca[key]==cb[key],key
        with np.load(left/ca['arrays_file'],allow_pickle=False) as fa,np.load(right/cb['arrays_file'],allow_pickle=False) as fb:
            assert fa.files==fb.files
            for key in fa.files:np.testing.assert_array_equal(fa[key],fb[key],err_msg=key)
        with np.load(left/'selected.npz',allow_pickle=False) as fa,np.load(right/'selected.npz',allow_pickle=False) as fb:
            for key in fa.files:np.testing.assert_array_equal(fa[key],fb[key])
        ra,rb=read(left/'report.json'),read(right/'report.json')
        assert ra['history']==rb['history'] and ra['best_epoch']==rb['best_epoch']
        if early:assert ra['epochs_run']==21 and ra['best_epoch']==1
    if point in ('before_registration','between_trials'):
        first=ledgers[1][0]['definition']['job_id']
        assert sum(e['kind']=='TRAIN_OR_RESUME_CALLED' and e['job_id']==first for e in read(b/'events.json'))==1


def sample():
    return dict(disk_free_bytes=10**12,power_query_ok=True,ac_connected=True,power_status='charging',battery_percent=80,
                process_query_ok=True,other_workers=[],available_memory_estimate_bytes=4*1024**3,
                thermal=dict(available=True,state=0,temperature_c=None))


@pytest.mark.parametrize('field,value,reason',[
    ('power_query_ok',False,'POWER_STATUS_NOT_VERIFIED'),
    ('power_status','discharging','BATTERY_DISCHARGING'),('available_memory_estimate_bytes',None,'AVAILABLE_MEMORY_BELOW_2_GIB_OR_UNKNOWN'),
    ('other_workers',[dict(pid=123)],'ANOTHER_PHASE11_WORKER'),('process_query_ok',False,'WORKER_QUERY_UNAVAILABLE')])
def test_runtime_gate_fails_closed(field,value,reason):
    from connectome.scripts.phase11.runtime import assess
    a=sample();b=sample();b[field]=value
    assert reason in assess(a,b,10**9)


def test_pressure_and_stable_ac_rules():
    from connectome.scripts.phase11.runtime import assess
    a=sample();b=sample();b['power_status']='not charging'
    assert assess(a,b,10**9)==[]
    b['battery_percent']=79
    assert 'CHARGING_OR_STABLE_NOT_VERIFIED' in assess(a,b,10**9)
    b=sample();b['thermal']['state']=2
    assert 'SERIOUS_OR_CRITICAL_THERMAL_PRESSURE' in assess(a,b,10**9)
    b['thermal']=dict(available=False,state=None,temperature_c=None)
    assert assess(a,b,10**9)==[]


@pytest.mark.parametrize('free',[0,10**8])
def test_disk_estimate_is_logged_but_does_not_block(monkeypatch,free):
    from connectome.scripts.phase11 import runtime
    row=sample();row['disk_free_bytes']=free
    monkeypatch.setattr(runtime,'sample',lambda:row.copy())
    monkeypatch.setattr(runtime.time,'sleep',lambda seconds:None)
    saved=[]
    monkeypatch.setattr(runtime,'write',lambda path,value:saved.append(value))
    result=runtime.check(10**9)
    assert result['status']=='PASS' and result['blockers']==[]
    assert result['warnings']==['DISK_BELOW_CONSERVATIVE_ESTIMATE']
    assert result['disk_policy']==dict(blocking=False,estimated_required_bytes=10**9)
    assert saved==[result]


@pytest.mark.parametrize('level,allowed',[(96,True),(21,True),(20,True),(19,False),(0,False),(None,False),(101,False)])
def test_battery_power_without_ac(level,allowed):
    from connectome.scripts.phase11.runtime import assess
    a=sample();b=sample()
    for row in (a,b):
        row.update(ac_connected=False,power_status='discharging',battery_percent=level)
    assert (assess(a,b,10**9)==[]) is allowed


def test_normal_battery_discharge_allowed_but_other_guards_remain():
    from connectome.scripts.phase11.runtime import assess
    a=sample();b=sample()
    a.update(ac_connected=False,power_status='discharging',battery_percent=96)
    b.update(ac_connected=False,power_status='discharging',battery_percent=95)
    assert assess(a,b,10**9)==[]
    b['thermal']['state']=2
    assert 'SERIOUS_OR_CRITICAL_THERMAL_PRESSURE' in assess(a,b,10**9)
    b['thermal']['state']=0;b['power_status']='unknown'
    assert 'BATTERY_POWER_STATUS_NOT_VERIFIED' in assess(a,b,10**9)


def test_continuous_launcher_has_no_session_limits_or_cooling():
    launch=(ROOT/'connectome/scripts/phase11/launch.py').read_text()
    assert "'continuous'" in launch and "'preflight'" in launch
    assert 'session_launch' not in launch and 'cooling_seconds' not in launch


def test_parent_ctrl_c_publishes_then_new_parent_resumes():
    directory=OUT/'tests/manual'/uuid.uuid4().hex
    cmd=[sys.executable,'-B','-m','connectome.scripts.phase11.tests.launcher_fixture','--directory',str(directory)]
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
    parent=subprocess.Popen(cmd+['--pause'],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    ready=directory/'copy/connectome/Results/phase11/results/fixture/ready.json'
    try:
        deadline=time.monotonic()+20
        while not ready.exists() and parent.poll() is None and time.monotonic()<deadline:time.sleep(.01)
        assert ready.exists()
        parent.send_signal(signal.SIGINT)
        stdout,stderr=parent.communicate(timeout=15)
        assert parent.returncode==130,(stdout,stderr)
    finally:
        if parent.poll() is None:parent.kill();parent.wait()
    canonical=directory/'canonical'
    assert read(canonical/'execution_fixture.json')['final_publication_completed']
    checkpoint=canonical/'fixture/training/fixture_0.0003/current.json'
    current=read(checkpoint)
    assert current['offset']==16 and current['adam_updates']==1
    assert sha(checkpoint.parent/current['arrays_file'])==current['arrays_sha256']
    resumed=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True,timeout=30)
    assert resumed.returncode==0,resumed.stderr
    complete=[e['job_id'] for e in read(canonical/'fixture/events.json') if e['kind']=='COMPLETE']
    assert len(complete)==len(set(complete))==2


def test_continuous_phase_order_and_completed_gate_reuse(monkeypatch):
    from connectome.scripts.phase11 import runner,jobs,runtime
    root=OUT/'tests/manual'/uuid.uuid4().hex
    definitions={'unit':'synthetic_only'}
    write(root/'gate_B.json',dict(status='PASS',phase11_sources_sha256=definitions))
    write(root/'gate_C.json',dict(status='PASS',phase11_sources_sha256=definitions,conservative_disk_allowance_bytes=1))
    monkeypatch.setattr(runner,'OUT',root);monkeypatch.setattr(runner,'sources',lambda:definitions)
    monkeypatch.setattr(runtime,'check',lambda _:dict(status='PASS'))
    calls=[]
    def execute(primary):calls.append(primary);return dict(status='PASS')
    monkeypatch.setattr(jobs,'execute',execute)
    monkeypatch.setattr(runner,'finish_freeze',lambda:calls.append('freeze'))
    monkeypatch.setattr(sys,'argv',['unit','--task','continuous'])
    runner.run();runner.run()
    assert calls==[True,False,'freeze','freeze']


@pytest.mark.parametrize('late',[False,True])
def test_completion_during_publication_refreshes_final_checkpoint(monkeypatch,late):
    from connectome.scripts.phase11 import launch
    from connectome.scripts.phase11.common import arrays
    base=OUT/'tests/manual'/uuid.uuid4().hex;source=base/'source';dest=base/'dest'
    trial=source/'training/unit';target=dest/'training/unit';target.mkdir(parents=True)
    arrays(trial/'state_000001.npz',x=np.array([1.]))
    write(trial/'current.json',dict(generation=1,arrays_file='state_000001.npz',arrays_sha256=sha(trial/'state_000001.npz')))
    write(source/'job_ledger.json',[dict(status='RUNNING_OR_RESUMING',definition=dict(job_id='unit'))])
    write(source/'trigger.json',dict(unit_only=True))
    if late:
        original_rglob=Path.rglob
        def rglob(path,pattern):
            result=original_rglob(path,pattern)
            return iter(list(result)) if path==source and pattern=='*' else result
        monkeypatch.setattr(Path,'rglob',rglob)
    original=launch.atomic;changed=False
    def atomic(path,data):
        nonlocal changed
        original(path,data)
        trigger=dest/'trigger.json' if late else target/'current.json'
        if path==trigger and not changed:
            changed=True
            arrays(trial/'state_000002.npz',x=np.array([2.]))
            write(trial/'current.json',dict(generation=2,arrays_file='state_000002.npz',arrays_sha256=sha(trial/'state_000002.npz')))
            arrays(trial/'selected.npz',x=np.array([2.]))
            write(trial/'report.json',dict(unit_only=True,parameters_sha256=sha(trial/'selected.npz')))
            write(source/'job_ledger.json',[dict(status='COMPLETE',definition=dict(job_id='unit'))])
    monkeypatch.setattr(launch,'atomic',atomic)
    launch.publish(source,dest)
    assert read(target/'current.json')['generation']==(1 if late else 2)
    if late:assert not (target/'report.json').exists()
    assert read(dest/'job_ledger.json')[0]['status']=='RUNNING_OR_RESUMING'
    launch.publish(source,dest)
    assert read(dest/'job_ledger.json')[0]['status']=='COMPLETE'
    assert sha(target/'selected.npz')==read(target/'report.json')['parameters_sha256']


def test_orphaned_worker_stops_at_next_committed_boundary(monkeypatch):
    from connectome.scripts.phase11 import manual_stop
    monkeypatch.setenv('FLY_PHASE11_LAUNCHER_PID','100')
    monkeypatch.setattr(manual_stop.os,'getppid',lambda:100)
    with manual_stop.handlers(watch_parent=True):
        manual_stop.boundary()
        monkeypatch.setattr(manual_stop.os,'getppid',lambda:1)
        with pytest.raises(manual_stop.Paused):manual_stop.boundary()
