import sys,json
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from connectome.scripts.phase11 import jobs
from connectome.scripts.phase11.common import OUT,sha,write
from connectome.scripts.phase11.dataset import Dataset
from connectome.scripts.phase7.pipeline import FrozenPipeline
paths=[p for folder in (OUT/'training',OUT/'selected') for p in folder.rglob('*') if p.is_file()]
before={str(p):sha(p) for p in paths}
rows=jobs.ledger();job=next(r['definition'] for r in rows if r['definition']['job_id']=='cal_uniform_population_gru_55100')
dataset=Dataset(FrozenPipeline(),'uniform_population');inputs=dataset.prepare();train=dataset.records('train');val=dataset.records('validation')
def forbidden(*args,**kwargs):raise AssertionError('Replay must not retrain, infer new neural responses or duplicate ledger registration')
jobs.train_trial=forbidden;jobs.score_model=forbidden;jobs.update=forbidden
net,artifacts=jobs.selected_gru('uniform_population',55100,train,val,inputs,rows)
proof=jobs.calibrate_job(job,dataset,train,val,inputs,net,artifacts)
jobs.verify_freeze(OUT/'calibration'/job['job_id']/'freeze.json')
assert before=={str(p):sha(p) for p in paths}
result=dict(status='PASS_DISPOSABLE_FULL_PATH_REPLAY',condition=job['job_id'],training_artifacts_unchanged=len(before),retraining_calls=0,new_neural_inference_calls=0,ledger_registration_calls=0,source_provenance_bridge_verified=True,freeze_verified=True,test_ids_used=proof['calibration']['test_ids_used'])
Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
