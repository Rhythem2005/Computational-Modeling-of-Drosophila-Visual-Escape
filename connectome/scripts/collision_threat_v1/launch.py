"""Stage A launcher: read-only lease and complete previous-artifact preservation."""
import argparse
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
from .common import ROOT,BASE,PLAN,SOURCE_RUN,read,sha,write,sources,inventory,Budget,rss,size,MAX_BYTES,require_stage_b_review

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--stage',choices=['saved-diagnostic','prototype'],default='saved-diagnostic')
    args=parser.parse_args()
    if args.stage=='prototype':require_stage_b_review(None)
    output=BASE/str(time.time_ns());output.mkdir(parents=True,exist_ok=False)
    budget=Budget(output);before=inventory();initial_sources=sources()
    write(output/'preservation_before.json',before)
    write(output/'authorization.json',dict(user_instruction='Approved.',
          approved_plan_sha256=sha(PLAN/'README.md'),scope='Stage A: <=91 saved trajectories, no inference/fitting/new episodes',
          exact_rule_review_reserved=True,stage_b_dispatch_enabled=False))
    write(output/'execution_manifest.json',dict(stage='saved-diagnostic',source_run=str(SOURCE_RUN.relative_to(ROOT)),
          source_manifest_sha256=sha(SOURCE_RUN/'manifest.json'),sources_sha256=initial_sources,
          maximum_unique_trajectories=91,limits=dict(seconds=900,rss_bytes=4*1024**3,output_bytes=MAX_BYTES),
          diagnostic_feature_api='frame,timestamp_s; camera constants only',new_simulations=0,new_model_inference=0))
    os.environ.setdefault('PYTHONDONTWRITEBYTECODE','1')
    os.environ['MPLCONFIGDIR']=str(output/'matplotlib_cache')
    try:
        with (ROOT/'connectome/Results/phase11/results/manual_worker.lock').open('r') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            from connectome.scripts.phase11.runtime import sample,assess
            first=sample();time.sleep(2);second=sample();errors=assess(first,second,MAX_BYTES)
            write(output/'resource_preflight.json',dict(samples=[first,second],blockers=errors,
                  disk_estimate_advisory=True,disk_warning=second['disk_free_bytes']<MAX_BYTES))
            if errors:raise RuntimeError('Resource startup gate: '+', '.join(errors))
            env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',VECLIB_MAXIMUM_THREADS='1')
            print(f'Stage A output: {output}',flush=True)
            with (output/'tests.log').open('w') as log:
                tests=subprocess.run([sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider',
                    'connectome/scripts/collision_threat_v1/tests',f'--junitxml={output/"tests.xml"}'],
                    env=env,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=max(1,900-(time.monotonic()-budget.start)))
            if tests.returncode:raise RuntimeError('Feature tests failed; saved-data processing blocked')
            budget.check()
            from .diagnose_saved import run
            result=run(output,budget)
            write(output/'execution.json',dict(status='COMPLETE_STAGE_A',elapsed_s=time.monotonic()-budget.start,
                  peak_rss_bytes=rss(),output_bytes=size(output),
                  new_simulations=0,new_model_inference=0,new_calibration=0,new_training=0,held_out_evaluations=0,
                  stage_a_review=result['stage_a_review'],stage_b_enabled=False))
            fcntl.flock(lock,fcntl.LOCK_UN)
    except BaseException as error:
        write(output/'failure.json',dict(type=type(error).__name__,error=str(error),traceback=traceback.format_exc(),
                                        partial_saved_diagnostic=True))
        raise
    finally:
        after=inventory();write(output/'preservation_after.json',after)
        unchanged=before==after
        same_sources=initial_sources==sources()
        write(output/'preservation.json',dict(unchanged=unchanged,files=len(before),new_sources_unchanged=same_sources))
        if not unchanged or not same_sources:raise RuntimeError('Earlier artifacts or active source changed')

if __name__=='__main__':main()
