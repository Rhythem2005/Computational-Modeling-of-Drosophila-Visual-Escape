"""Physical evidence is independent of visual estimates; no forced success labels."""
from pathlib import Path
import json,math,shutil
import numpy as np
from ..avoidance.recording import atomic_json
from ..avoidance.contracts import digest
from .geometry import contact_part

def metrics(c,scene,a,failure,commands):
    times=a['world_times_ms'];fly=a['fly_position'];per=[];encounters=[]
    for solid in (*scene.static_solids,*scene.dynamic_solids):
        clears=[]
        for j in range(len(times)-1):
            center=solid.position(times[j]);delta=solid.position(times[j+1])-center
            clear=min(contact_part(fly[j],fly[j+1]-fly[j],center,delta,p,c.motion.fly_radius)[1] for p in solid.parts);clears.append(clear)
        last=min(contact_part(fly[-1],np.zeros(3),solid.position(times[-1]),np.zeros(3),p,c.motion.fly_radius)[1] for p in solid.parts)
        per.append(dict(id=solid.id,minimum_swept_clearance=float(min(clears)),final_clearance=float(last),segment_clearances=clears))
    bounds=np.asarray(c.motion.bounds)+np.array([c.motion.fly_radius,-c.motion.fly_radius]);wall=float(np.minimum(fly-bounds[:,0],bounds[:,1]-fly).min())
    minimum=min([wall]+[r['minimum_swept_clearance'] for r in per]);final=min([float(np.minimum(fly[-1]-bounds[:,0],bounds[:,1]-fly[-1]).min())]+[r['final_clearance'] for r in per])
    request_times=a['decision_times_ms'][a['escape_event']].tolist()
    for e in scene.encounters:
        segments=[i for i,t in enumerate(times[:-1]) if t<e['end_ms'] and times[i+1]>e['start_ms']]
        clear=min((r['segment_clearances'][j] for r in per if r['id'] in e['object_ids'] for j in segments),default=None)
        encounters.append(dict(**e,observed_until_ms=float(times[-1]),fully_observed=bool(times[-1]>=e['end_ms']),minimum_clearance=clear,request_times_ms=[t for t in request_times if e['start_ms']<=t<e['end_ms']],danger=None,false_alarm=None,adjudication='Requires paired ordinary-motion baseline; mixed/overlapping windows never blamed on a harmless distractor'))
    for r in per:r.pop('segment_clearances')
    return dict(danger=None,escape_success=None,false_alarm=None,failure=failure,end_ms=float(times[-1]),survived_horizon=bool(failure is None and times[-1]==c.motion.duration_ms),minimum_swept_clearance=float(minimum),final_clearance=float(final),per_object=per,encounters=encounters,path_length=float(np.linalg.norm(np.diff(fly,axis=0),axis=-1).sum()),request_count=len(request_times),motor_command_count=len(commands),endpoint_scope='Physical room contacts; task labels await baseline encounter adjudication')

def audit(c,scene,a,m):
    if any(v.dtype==object for v in a.values()):raise ValueError('Object arrays prohibited')
    t=a['world_times_ms'];dt=a['decision_times_ms'];ft=a['frame_timestamps_s'];q=a['fly_quaternion_xyzw']
    if not np.array_equal(dt,np.arange(len(dt))) or not np.all(np.diff(t)>0) or dt[-1]>=t[-1] or t[-1]>c.motion.duration_ms:raise ValueError('Invalid causal/terminal room clocks')
    if not np.all(np.diff(ft)>0) or ft[-1]>t[-1]/1000:raise ValueError('Invalid camera timestamps')
    np.testing.assert_array_equal(a['decision_frame_indices'],np.searchsorted(ft,dt/1000,side='right')-1)
    np.testing.assert_array_equal(a['decision_drive_unscaled'],a['frame_drive'][a['decision_frame_indices']])
    if not np.isfinite(a['fly_position']).all() or not np.isfinite(q).all() or not np.allclose((q*q).sum(axis=1),1,atol=1e-10):raise ValueError('Invalid body pose')
    if np.any(np.linalg.norm(np.diff(a['fly_position'],axis=0),axis=1)/(np.diff(t)/1000)>c.motion.escape_speed_max+1e-8):raise ValueError('Speed cap exceeded')
    if len(a['controller_states'])!=len(a['controller_state_times_ms']):raise ValueError('Neural clock mismatch')
    # Independently replay the saved physical segments, not the model's estimates.
    found=[];minimum=float('inf')
    for i in range(len(t)-1):
        for solid in (*scene.static_solids,*scene.dynamic_solids):
            p=solid.position(t[i]);d=solid.position(t[i+1])-p
            for part in solid.parts:
                hit,clear=contact_part(a['fly_position'][i],a['fly_position'][i+1]-a['fly_position'][i],p,d,part,c.motion.fly_radius);minimum=min(minimum,clear)
                if hit is not None:found.append((t[i]+hit*(t[i+1]-t[i]),solid.id))
    wall=np.asarray(c.motion.bounds)+np.array([c.motion.fly_radius,-c.motion.fly_radius])
    wall_clear=float(np.minimum(a['fly_position']-wall[:,0],wall[:,1]-a['fly_position']).min())
    minimum=min(minimum,wall_clear)
    if not math.isclose(minimum,m['minimum_swept_clearance'],abs_tol=1e-8,rel_tol=1e-8):raise ValueError('Independent room clearance disagreement')
    if wall_clear < -1e-8:raise ValueError('Unreported room boundary penetration')
    if m['failure'] is not None and m['failure']['kind']=='boundary' and not math.isclose(wall_clear,0,abs_tol=1e-8):raise ValueError('Boundary event lacks contact geometry')
    velocity=a['fly_velocity'];steps=np.diff(t)/1000
    np.testing.assert_allclose(np.diff(a['fly_position'],axis=0)/steps[:,None],velocity[:-1],atol=1e-8)
    if np.any(np.linalg.norm(np.diff(velocity,axis=0),axis=1)/steps>c.motion.escape_acceleration_max+1e-6):raise ValueError('Acceleration limit exceeded')
    angle=2*np.arccos(np.clip(np.abs(np.sum(q[:-1]*q[1:],axis=1)),0,1))
    if np.any(angle>c.max_heading_rate_rad_s*steps+1e-6):raise ValueError('Heading rate exceeds model limit')
    if found and m['failure'] is None:raise ValueError('Unreported physical contact')
    if found and not math.isclose(min(t for t,_ in found),t[-1],abs_tol=1e-8):raise ValueError('Contact time does not match terminal clock')
    if m['failure'] is not None and not math.isclose(m['failure']['time_ms'],t[-1],abs_tol=1e-8):raise ValueError('Failure endpoint mismatch')
    return True

def save(folder,run,c,scene):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=False)
    if any(a.dtype==object for a in run['arrays'].values()):raise ValueError('Object arrays cannot be saved')
    path=folder/'arrays.npz';np.savez_compressed(path,schema_version=np.array('room_flight_1.0'),**run['arrays'])
    raw={k:v for k,v in run.items() if k!='arrays'};raw.update(arrays_sha256=digest(path),status='COMPUTED_PENDING_AUDIT',protocol='room_flight_engineering_v1')
    atomic_json(folder/'computed.json',raw)
    try:audit(c,scene,run['arrays'],run['metrics'])
    except Exception as e:atomic_json(folder/'audit_failure.json',dict(error=str(e),computation_preserved=True));raise
    raw.update(status='COMPLETE_PHYSICAL_RECORDING_TASK_ADJUDICATION_SEPARATE',independent_metric_check=True);atomic_json(folder/'verified.json',raw)
    catalog=folder.parent.parent/'episodes';catalog.mkdir(exist_ok=True);shutil.copyfile(path,catalog/(folder.name+'.npz'));atomic_json(catalog/(folder.name+'.json'),raw)
    return raw

def adjudicate(records):
    """No new simulation: use completed ordinary-motion recordings as counterfactuals."""
    results=[];by_scene={}
    for r in records:by_scene.setdefault(r['scenario']['scenario_id'],{})[r['model']]=r
    for case,models in by_scene.items():
        baseline=models.get('ordinary_motion')
        for model,r in models.items():
            m=r['metrics'];row=dict(scenario=case,model=model,collision=m['failure'],survived_horizon=m['survived_horizon'],encounters=[])
            if baseline is None:row['status']='baseline_missing'
            else:
                row['status']='baseline_adjudicated_with_visibility_limits'
                for encounter in m['encounters']:
                    b=next((e for e in baseline['metrics']['encounters'] if e['id']==encounter['id']),None)
                    fully=b is not None and b['fully_observed'];failed=baseline['metrics']['failure']
                    hit=failed is not None and failed['object_id'] in encounter['object_ids'] and encounter['start_ms']<=failed['time_ms']<encounter['end_ms']
                    danger=True if hit else False if fully and b['minimum_clearance'] is not None and b['minimum_clearance']>0 else None
                    mixed=any(e['id']!=encounter['id'] and max(e['start_ms'],encounter['start_ms'])<min(e['end_ms'],encounter['end_ms']) for e in m['encounters'])
                    row['encounters'].append(dict(id=encounter['id'],danger=danger,false_alarm=None if mixed or danger is None else bool(not danger and encounter['request_times_ms']),avoidance_success=None if danger is not True else bool(m['failure'] is None and m['final_clearance']>=r['config']['success_final_clearance_min'] and encounter['fully_observed'] and encounter['minimum_clearance'] is not None and encounter['minimum_clearance']>0)))
            results.append(row)
    return results
