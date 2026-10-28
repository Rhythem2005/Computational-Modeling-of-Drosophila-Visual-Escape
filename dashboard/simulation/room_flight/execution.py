"""Durable snapshot and bounded execution preflight, before any reservation."""
from pathlib import Path
import json,shutil,time
from ..avoidance.contracts import digest
from ..avoidance.recording import atomic_json
ROOT=Path(__file__).resolve().parents[3]

def unattempted_jobs(jobs,ledger,protocol_sha256,output):
    """Continuation consumes only untouched jobs; failures/reservations stay consumed."""
    if ledger.get('protocol_sha256')!=protocol_sha256 or ledger.get('cap')!=24 or ledger.get('output')!=str(output):raise ValueError('Continuation budget/protocol/output differs')
    known={j['id']:j for j in jobs};seen=set()
    for attempt in ledger['attempts']:
        job=attempt['job'];identity=job['id']
        if identity in seen or identity not in known or known[identity]!=job or attempt['status'] not in ('RESERVED','COMPLETE','FAILED','INTERRUPTED'):raise ValueError('Invalid or duplicated consumed room attempt')
        seen.add(identity)
    if len(seen)>24 or not 0<=ledger.get('elapsed_seconds',0):raise ValueError('Invalid cumulative budget')
    return [j for j in jobs if j['id'] not in seen]

def durable_snapshot(record_path):
    record=json.loads(Path(record_path).read_text());old=Path(record['path']);expected=record['files_sha256']
    if not all((old/n).is_file() and digest(old/n)==h for n,h in expected.items()):
        from connectome.scripts.collision_threat_v2.launch import snapshot
        old,copied=snapshot()
        if not all((old/n).is_file() and digest(old/n)==h for n,h in expected.items()):raise ValueError('Historical compatibility reconstruction differs')
    target=ROOT/'dashboard/.runtime'/('room_snapshot_'+digest(record_path)[:16])
    target.mkdir(parents=True,exist_ok=True)
    for name,h in expected.items():
        destination=target/name
        if destination.exists():
            if digest(destination)!=h:raise ValueError('Durable snapshot was changed: '+name)
        else:
            destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/name,destination)
            if digest(destination)!=h:raise ValueError('Snapshot copy hash mismatch')
    result=dict(record,path=str(target));saved=target.parent/(target.name+'.json');atomic_json(saved,result)
    return saved

def protected_fingerprints():
    pointers=[ROOT/'connectome/Results/phase11/results/job_ledger.json',ROOT/'connectome/Results/phase11/results/training/train_55011_55102_0p001/current.json']
    current=json.loads(pointers[-1].read_text());pointers.append(pointers[-1].parent/current['arrays_file'])
    return {str(p.relative_to(ROOT)):digest(p) for p in [*pointers,*(ROOT/'connectome/scripts').rglob('*.py')]}
