"""Evidence and hard bounds, independent of the frozen experiment writers."""
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'connectome/Results/collision_threat_v1'
SOURCE_RUN=ROOT/'connectome/Results/behavior_validation/1793090166386522000'
PLAN=ROOT/'connectome/Results/collision_threat_implementation_plan_20261027'
MAX_SAVED_EPISODES=91
MAX_BYTES=250*1024**2
MAX_RSS=4*1024**3

def read(path):return json.loads(Path(path).read_text())

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def write(path,obj):
    path=Path(path)
    if not path.resolve().is_relative_to(BASE.resolve()):
        raise ValueError('New evidence must remain in the new collision-threat namespace')
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.tmp')
    tmp.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n');os.replace(tmp,path)

def sources():
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted(Path(__file__).parent.rglob('*.py'))}

def inventory():
    result={}
    for name in ('connectome/Results','connectome/scripts'):
        for p in (ROOT/name).rglob('*'):
            if (p.is_file() and 'collision_threat_v1' not in p.relative_to(ROOT/name).parts
                    and not {'__pycache__','.pytest_cache'}.intersection(p.parts)):
                result[str(p.relative_to(ROOT))]=sha(p)
    for name in ('README.md','config.yaml','requirements.txt','STUDY_CHECKPOINT.md'):
        if (ROOT/name).exists():result[name]=sha(ROOT/name)
    return result

def rss():
    n=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(n if sys.platform=='darwin' else n*1024)

def size(path):return sum(p.stat().st_size for p in Path(path).rglob('*') if p.is_file())

class Budget:
    def __init__(self,path):self.path=path;self.start=time.monotonic()
    def check(self):
        if time.monotonic()-self.start>900:raise RuntimeError('STAGE_A_15_MINUTE_BUDGET')
        if rss()>MAX_RSS:raise RuntimeError('STAGE_A_4_GIB_RSS_BUDGET')
        if size(self.path)>MAX_BYTES:raise RuntimeError('STAGE_A_250_MIB_OUTPUT_BUDGET')

def require_stage_b_review(review_path):
    """Fail closed: plan approval does not fill in the reserved exact-rule review."""
    if review_path is None:
        raise ValueError('Stage B disabled pending the reviewed exact decision-rule specification')
    review=read(review_path)
    if review.get('status')!='USER_APPROVED_EXACT_RULE_MANIFEST':
        raise ValueError('Missing exact-rule review authorization')
    raise NotImplementedError('Prototype dispatcher is not enabled by the Stage A implementation')
