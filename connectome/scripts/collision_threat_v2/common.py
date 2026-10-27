"""Scoped scientific preservation, deliberately excluding parallel dashboard work."""
import hashlib
import json
import os
from pathlib import Path
import resource
import sys

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'connectome/Results/collision_threat_v2'
PLAN=ROOT/'connectome/Results/finite_body_gate_plan_20261027'
V1=ROOT/'connectome/Results/collision_threat_v1'
REFERENCE=V1/'prototype/1793093607177149000'
PROTOCOL='known_size_finite_body_retirement_gate_v2'

def read(path):return json.loads(Path(path).read_text())
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def write(path,obj):
    root=Path(os.environ.get('FLY_V2_OUTPUT',str(BASE))).resolve()
    path=Path(path)
    if not path.resolve().is_relative_to(root):raise ValueError('Output escapes authorized new namespace')
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.tmp')
    tmp.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n');os.replace(tmp,path)

def sources():
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted(Path(__file__).parent.rglob('*.py'))}

def protected_names():
    # Fixed earlier scientific filenames, NOT a scan of the user's changing repo.
    old=read(REFERENCE/'preservation_before.json')
    names={n for n in old if n.startswith('connectome/') or n in ('config.yaml','requirements.txt')}
    for base in (V1,PLAN):
        names.update(str(p.relative_to(ROOT)) for p in base.rglob('*') if p.is_file()
                     and not {'__pycache__','.pytest_cache'}.intersection(p.parts))
    return sorted(names)

def inventory(names):return {n:sha(ROOT/n) for n in names}
def size(path):return sum(p.stat().st_size for p in Path(path).rglob('*') if p.is_file())
def rss():
    x=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(x if sys.platform=='darwin' else x*1024)

def verify_plan():
    proof=read(PLAN/'evidence_snapshot.json')
    if sha(PLAN/'README.md')!=proof['plan_sha256'] or sha(PLAN/'proposed_protocol.json')!=proof['proposed_protocol_sha256']:
        raise ValueError('Approved plan/proposal changed')
    for name,h in {**proof['evidence_sha256'],**proof['production_pointers_sha256']}.items():
        if sha(ROOT/name)!=h:raise ValueError(f'Bound scientific artifact changed: {name}')
        if name.endswith('/current.json'):
            checkpoint=read(ROOT/name)
            if sha((ROOT/name).parent/checkpoint['arrays_file'])!=checkpoint['arrays_sha256']:
                raise ValueError('Partial checkpoint payload changed')
    for name,h in read(REFERENCE/'manifest.json')['sources_sha256'].items():
        if sha(ROOT/name)!=h:raise ValueError(f'Frozen v1 source changed: {name}')
    if len(read(V1/'prototype/attempt_ledger.json')['attempts'])!=60:
        raise ValueError('Historical v1 attempt ledger changed')
    proposal=read(PLAN/'proposed_protocol.json')
    if len(proposal['jobs'])!=80 or len({j['episode_id'] for j in proposal['jobs']})!=80:
        raise ValueError('Proposed condition coverage differs')
    return proposal
