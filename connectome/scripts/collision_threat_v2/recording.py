"""v2 schema, with unchanged finite-fly independent metric checking."""
from pathlib import Path
import numpy as np
from connectome.scripts.behavior_validation.evidence import verify_metrics
from .common import write,read,sha,PROTOCOL

def save_episode(directory,ident,run):
    path=Path(directory)/f'{ident}.npz';meta=path.with_suffix('.json')
    if path.exists() or meta.exists():raise FileExistsError('No attempt overwrite')
    path.parent.mkdir(parents=True,exist_ok=True);verify_metrics(run)
    np.savez_compressed(path,schema_version=np.array('collision_threat_2.0'),**run['arrays'])
    record={k:v for k,v in run.items() if k!='arrays'}
    record.update(protocol=PROTOCOL,arrays_sha256=sha(path),independent_metric_check=True)
    write(meta,record)
    loaded=load_episode(directory,ident)
    for key,value in run['arrays'].items():np.testing.assert_array_equal(value,loaded['arrays'][key])

def load_episode(directory,ident):
    path=Path(directory)/f'{ident}.npz';record=read(path.with_suffix('.json'))
    if record['protocol']!=PROTOCOL or sha(path)!=record['arrays_sha256']:raise ValueError('Episode identity/hash changed')
    with np.load(path,allow_pickle=False) as f:
        if f['schema_version'].item()!='collision_threat_2.0':raise ValueError('Unknown schema')
        arrays={k:f[k].copy() for k in f.files if k!='schema_version'}
    result=dict(record,arrays=arrays);verify_metrics(result);return result
