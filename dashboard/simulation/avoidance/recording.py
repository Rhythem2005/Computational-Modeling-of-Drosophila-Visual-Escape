"""Durable evidence first, independent endpoint audit second, publication last."""
from dataclasses import asdict
from pathlib import Path
import json,os
import numpy as np
from .world import swept_contact
from .contracts import digest

def atomic_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');os.replace(tmp,path)

def calculate_metrics(c,scenario,a,failure,commands):
    times=a['world_times_ms'];flies=a['fly_position'];objects=a['obstacle_positions']
    radius=np.array([o['radius'] for o in scenario.obstacles])+c.fly_radius
    rel=objects-flies[:,None,:];p=rel[:-1];d=np.diff(rel,axis=0);dd=(d*d).sum(-1)
    fraction=np.divide(-(p*d).sum(-1),dd,out=np.zeros_like(dd),where=dd>0)
    segment_clearance=np.linalg.norm(p+np.clip(fraction,0,1)[...,None]*d,axis=-1)-radius
    minimum=float(segment_clearance.min());final=float((np.linalg.norm(rel[-1],axis=-1)-radius).min())
    contacts=[]
    for ob in scenario.obstacles:
        horizon=c.duration_ms-ob['onset_ms'];hit,_=swept_contact(np.array(ob['position'])-scenario.fly_position,np.array(ob['velocity'])*horizon/1000,ob['radius']+c.fly_radius)
        if hit is not None:contacts.append(ob['onset_ms']+hit*horizon)
    danger=bool(contacts);stationary=min(contacts) if contacts else None
    requests=np.flatnonzero(a['escape_event']);request=float(a['decision_times_ms'][requests[0]]) if len(requests) else None
    survived=failure is None and times[-1]==c.duration_ms and minimum>0
    timely=request is not None and (stationary is None or request<stationary)
    per_object=[dict(id=o['id'],minimum_swept_clearance=float(segment_clearance[:,i].min()),final_clearance=float(np.linalg.norm(rel[-1,i])-radius[i])) for i,o in enumerate(scenario.obstacles)]
    return dict(per_object=per_object,danger=danger,stationary_contact_ms=stationary,escape_success=None if not danger else bool(timely and survived and final>=c.success_final_clearance_min),
        false_alarm=bool(not danger and len(requests)),dangerous_miss=bool(danger and not timely),
        failure=failure,end_ms=float(times[-1]),survived_horizon=bool(survived),minimum_swept_clearance=minimum,final_clearance=final,
        path_length=float(np.linalg.norm(np.diff(flies,axis=0),axis=-1).sum()),request_count=len(requests),motor_command_count=len(commands),
        endpoint_scope='stationary-fly whole-scene danger; not a per-object causal false-alarm adjudication')

def audit_arrays(c,scenario,a,metrics,commands):
    if any(v.dtype==object for v in a.values()):raise ValueError('Pickled/object arrays prohibited')
    t=a['world_times_ms'];dt=a['decision_times_ms'];ft=a['frame_timestamps_s']
    if not (np.all(np.diff(t)>0) and np.array_equal(dt,np.arange(len(dt))) and dt[-1]<t[-1]<=c.duration_ms):raise ValueError('Invalid world/decision endpoint')
    if np.any(np.diff(ft)<=0) or ft[-1]*1000>t[-1]:raise ValueError('Invalid camera clock')
    indices=np.searchsorted(ft,dt/1000,side='right')-1
    # Runner uses ms camera availability; enforce the frozen seconds comparison too.
    np.testing.assert_array_equal(indices,a['decision_frame_indices'])
    np.testing.assert_array_equal(a['decision_drive_unscaled'],a['frame_drive'][indices])
    if not np.isfinite(a['controller_states']).all():raise ValueError('Nonfinite neural state')
    if np.any(a['speed']>c.escape_speed_max+1e-10):raise ValueError('Speed cap exceeded')
    derived=np.linalg.norm(np.diff(a['fly_position'],axis=0),axis=-1)/(np.diff(t)/1000)
    if np.any(derived>c.escape_speed_max+1e-8):raise ValueError('Physical displacement exceeds speed cap')
    # Independently traverse saved segments; do not call the vectorized metric producer.
    clearances=[]
    for j in range(len(t)-1):
        for i,ob in enumerate(scenario.obstacles):
            start=a['obstacle_positions'][j,i]-a['fly_position'][j]
            end=a['obstacle_positions'][j+1,i]-a['fly_position'][j+1]
            _,clear=swept_contact(start,end-start,ob['radius']+c.fly_radius);clearances.append(clear)
    import math
    final=min(math.dist(a['fly_position'][-1],a['obstacle_positions'][-1,i])-o['radius']-c.fly_radius for i,o in enumerate(scenario.obstacles))
    distance=sum(math.dist(x,y) for x,y in zip(a['fly_position'][:-1],a['fly_position'][1:]))
    for key,value in [('minimum_swept_clearance',min(clearances)),('final_clearance',final),('path_length',distance)]:
        if not math.isclose(value,metrics[key],abs_tol=1e-10,rel_tol=1e-10):raise ValueError('Independent metric disagreement: '+key)
    failure=metrics['failure']
    if failure is None and min(clearances)<=0:raise ValueError('Unreported physical contact')
    if failure is not None and not math.isclose(failure['time_ms'],t[-1],abs_tol=1e-10):raise ValueError('Terminal failure time mismatch')
    event_indices=np.flatnonzero(a['escape_event']);first=None if not len(event_indices) else float(dt[event_indices[0]])
    if first!=metrics['first_request_ms']:raise ValueError('Request timing mismatch')
    moving=np.flatnonzero(np.any(np.diff(a['fly_position'],axis=0)!=0,axis=1))
    first_motion=None if not len(moving) else float(t[moving[0]])
    if first_motion!=metrics['first_motion_ms']:raise ValueError('Movement timing mismatch')
    if len(a['controller_states'])!=len(a['controller_state_times_ms']):raise ValueError('State clock mismatch')
    return True

def save_attempt(folder,run,c,scenario):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=False)
    a=run['arrays'];payload=folder/'arrays.npz'
    if any(v.dtype==object for v in a.values()):raise ValueError('Object arrays not allowed')
    np.savez_compressed(payload,schema_version=np.array('multi_object_1.0'),**a)
    raw={k:v for k,v in run.items() if k!='arrays'}
    raw.update(arrays_sha256=digest(payload),schema='multi_object_1.0',status='COMPUTED_PENDING_AUDIT')
    atomic_json(folder/'computed.json',raw)
    try:audit_arrays(c,scenario,a,run['metrics'],run['commands'])
    except Exception as e:
        atomic_json(folder/'audit_failure.json',dict(error=str(e),recording_preserved=True));raise
    raw.update(status='COMPLETE_ENGINEERING_DEMONSTRATION',independent_metric_check=True)
    atomic_json(folder/'verified.json',raw)
    # This small pair is the only catalog-visible commit point.
    catalog=folder.parent.parent/'episodes';catalog.mkdir(exist_ok=True)
    import shutil
    destination=catalog/(folder.name+'.npz');shutil.copyfile(payload,destination)
    atomic_json(catalog/(folder.name+'.json'),raw)
    return raw
