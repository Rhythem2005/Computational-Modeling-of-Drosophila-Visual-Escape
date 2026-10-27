"""New schema and independently calculated geometry/timing endpoints."""
import io
from pathlib import Path
import numpy as np
from .common import write, read, sha, PROTOCOL

def verify_metrics(run):
    a, m, c, s = run['arrays'], run['metrics'], run['config'], run['scenario']
    t = a['world_times_ms']; fly = a['fly_position']; obs = a['obstacle_positions']
    radii = np.array([o['radius'] for o in s['obstacles']])+c['fly_radius']
    relative = obs-fly[:,None,:]
    p, d = relative[:-1], np.diff(relative, axis=0)
    denom = (d*d).sum(-1)
    fraction = np.divide(-(p*d).sum(-1), denom, out=np.zeros_like(denom), where=denom>0)
    closest = p+np.clip(fraction,0,1)[...,None]*d
    minimum = float((np.linalg.norm(closest,axis=-1)-radii).min())
    final = float((np.linalg.norm(relative[-1],axis=-1)-radii).min())
    distance = np.linalg.norm(np.diff(fly,axis=0),axis=-1)
    moves = np.flatnonzero(distance>0)
    first_motion = None if not len(moves) else float(t[moves[0]])
    events = np.flatnonzero(a['escape_event'])
    assert len(events)<=1
    request = None if not len(events) else float(a['decision_times_ms'][events[0]])
    assert request == m['first_request_ms'] and first_motion == m['first_motion_ms']
    if request is not None:
        assert m['scheduled_actuation_ms'] == request+c['actuation_delay_ms']
        assert first_motion is None or first_motion >= m['scheduled_actuation_ms']
    for actual, recorded in ((minimum,m['minimum_swept_clearance']), (final,m['final_clearance']),
                             (float(distance.sum()),m['path_length'])):
        assert np.isclose(actual,recorded,atol=1e-12,rtol=1e-12)
    contacts = []
    for ob,radius in zip(s['obstacles'], radii):
        origin = np.array(ob['position'])-s['fly_position']; v = np.array(ob['velocity'])
        aa = float(v@v); bb = float(2*(origin@v)); cc = float(origin@origin-radius**2)
        if cc <= 0:
            contacts.append(0.)
        elif aa>0 and bb*bb-4*aa*cc>=0:
            entry = (-bb-np.sqrt(bb*bb-4*aa*cc))/(2*aa)
            if 0 <= entry <= (c['duration_ms']-c['obstacle_motion_onset_ms'])/1000:
                contacts.append(c['obstacle_motion_onset_ms']+entry*1000)
    assert bool(contacts) == m['danger']
    if contacts:
        assert np.isclose(min(contacts),m['stationary_contact_ms'])
    bounds = np.asarray(c['bounds_xy'])+np.array([c['fly_radius'],-c['fly_radius']])
    inside = bool(np.all(fly > bounds[:,0]) and np.all(fly < bounds[:,1]))
    survived = bool(t[-1]==1000 and minimum>0 and inside and not m['terminated'])
    assert survived == m['survived_horizon']
    timely = request is not None and (not contacts or request < min(contacts))
    success = None if not contacts else bool(timely and survived and final>=c['success_final_clearance_min'])
    assert success == m['escape_success']
    assert bool(not contacts and request is not None) == m['false_alarm']
    assert bool(contacts and not timely) == m['dangerous_miss']
    assert a['decision_times_ms'][-1] < min(1000,t[-1])
    assert len(a['controller_states']) == int(t[-1])+1
    assert len(a['frame_valid']) == m['frame_count']
    assert np.isfinite(a['controller_states']).all()
    if m['model']=='no_action':
        np.testing.assert_array_equal(fly,np.broadcast_to(s['fly_position'],fly.shape))
        assert request is None and m['path_length']==0

def save_episode(directory, episode_id, run):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    npz, meta = directory/(episode_id+'.npz'), directory/(episode_id+'.json')
    if npz.exists() or meta.exists():
        raise FileExistsError('Never overwrite an attempt')
    verify_metrics(run)
    np.savez_compressed(npz, schema_version=np.array('behavior_1.0'), **run['arrays'])
    record = {k:v for k,v in run.items() if k!='arrays'}
    record.update(protocol=PROTOCOL, arrays_sha256=sha(npz), independent_metric_check=True)
    write(meta,record)
    loaded = load_episode(directory,episode_id)
    for key in run['arrays']:
        np.testing.assert_array_equal(run['arrays'][key],loaded['arrays'][key])
    return record

def load_episode(directory,episode_id):
    directory=Path(directory)
    metadata=read(directory/(episode_id+'.json'))
    npz=directory/(episode_id+'.npz')
    if metadata['protocol']!=PROTOCOL or sha(npz)!=metadata['arrays_sha256']:
        raise ValueError('Episode identity/hash mismatch')
    with np.load(npz,allow_pickle=False) as f:
        if f['schema_version'].item()!='behavior_1.0':
            raise ValueError('Unsupported schema')
        arrays={k:f[k].copy() for k in f.files if k!='schema_version'}
    run=dict(metadata,arrays=arrays)
    verify_metrics(run)
    return run
