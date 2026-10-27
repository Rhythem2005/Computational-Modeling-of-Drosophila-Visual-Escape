"""New prototype schema; evaluator checks use the preserved trajectory checker."""
import os
from pathlib import Path
import json
import numpy as np
from connectome.scripts.behavior_validation.evidence import verify_metrics
from .common import BASE,read,sha

PROTOCOL='image_constant_velocity_point_observer_v1'

def allowed(path):
    root=Path(os.environ.get('FLY_COLLISION_OUTPUT',str(BASE/'prototype'))).resolve()
    if not Path(path).resolve().is_relative_to(root):raise ValueError('Output escapes new prototype directory')

def write(path,obj):
    path=Path(path);allowed(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.tmp')
    tmp.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n');os.replace(tmp,path)

def save_episode(directory,ident,run):
    directory=Path(directory);allowed(directory);directory.mkdir(parents=True,exist_ok=True)
    path=directory/f'{ident}.npz';meta=path.with_suffix('.json')
    if path.exists() or meta.exists():raise FileExistsError('Attempt already exists')
    verify_metrics(run)
    np.savez_compressed(path,schema_version=np.array('collision_threat_1.0'),**run['arrays'])
    record={k:v for k,v in run.items() if k!='arrays'}
    record.update(protocol=PROTOCOL,arrays_sha256=sha(path),independent_metric_check=True)
    write(meta,record)
    loaded=load_episode(directory,ident)
    for key in run['arrays']:np.testing.assert_array_equal(run['arrays'][key],loaded['arrays'][key])
    return record

def load_episode(directory,ident):
    directory=Path(directory);path=directory/f'{ident}.npz';record=read(path.with_suffix('.json'))
    if record['protocol']!=PROTOCOL or sha(path)!=record['arrays_sha256']:raise ValueError('Episode identity changed')
    with np.load(path,allow_pickle=False) as f:
        if f['schema_version'].item()!='collision_threat_1.0':raise ValueError('Unsupported prototype schema')
        arrays={k:f[k].copy() for k in f.files if k!='schema_version'}
    result=dict(record,arrays=arrays);verify_metrics(result)
    return result
