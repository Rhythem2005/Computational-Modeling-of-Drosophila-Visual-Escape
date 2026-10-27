import sys,json,time,statistics,pathlib,resource,numpy as np
sys.path.insert(0,sys.argv[1])
from connectome.scripts.phase7.pipeline import FrozenPipeline
from connectome.scripts.phase11.dataset import Dataset
from connectome.scripts.phase10.models import rate_trace,score_model
from connectome.scripts.phase10.networks import load_network
from connectome.scripts.phase10.gru import GRU
p=FrozenPipeline();d=Dataset(p,'uniform_population');d.prepare();drive=d.load('train_f0000_looming');w,setting,_=load_network('circuit',p.circuit);net=GRU(seed=55100)
r={}
for name,fn in [('reference_rate_clip',lambda:rate_trace(drive,p,w,setting)),('gru_score_single_clip',lambda:score_model('gru',drive,p,gru=net))]:
 t=time.perf_counter();fn();warm=time.perf_counter()-t;samples=[]
 for _ in range(9):
  t=time.perf_counter();fn();samples.append(time.perf_counter()-t)
 r[name]={'warmup_s':warm,'repetitions':len(samples),'samples_s':samples,'median_s':statistics.median(samples)}
r['maximum_resident_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
r['purpose']='Training-clip component timings only; no threshold selection, fitting or held-out inference'
pathlib.Path(sys.argv[2]).write_text(json.dumps(r,indent=2)+'\n')
print({k:v['median_s'] for k,v in r.items() if isinstance(v,dict)})
