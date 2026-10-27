"""Authorized single-candidate worker; no search, training or new-world evaluation."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import numpy as np
import yaml
from .common import ROOT,BASE,SOURCE_RUN,read,sha,sources,rss,size
from .features import camera_from_config
from .protocol import authorization,legacy_rows
from .hybrid import MODELS
from .prototype_runner import PrototypeRunner
from .prototype_io import write,save_episode,load_episode,PROTOCOL

class Budget:
    def __init__(self,output):self.output=output;self.start=time.monotonic();self.last_size=-float('inf')
    def check(self):
        if time.monotonic()-self.start>900:raise RuntimeError('PROTOTYPE_15_MINUTE_BUDGET')
        if rss()>4*1024**3:raise RuntimeError('PROTOTYPE_4_GIB_RSS_BUDGET')
        if time.monotonic()-self.last_size>=1:
            if size(self.output)+size(ROOT)>1024**3:raise RuntimeError('PROTOTYPE_OUTPUT_SNAPSHOT_BUDGET')
            self.last_size=time.monotonic()
        from connectome.scripts.phase11.runtime import thermal
        t=thermal()
        if t['available'] and t['state']>=2:raise RuntimeError('THERMAL_PRESSURE')

def jobs(scenarios):
    result=[]
    for s in scenarios:
        for model in MODELS:
            for repeat in (0,1):
                result.append(dict(id=f"{s['scenario_id']}_{model}_r{repeat}",scenario=s['scenario_id'],model=model,repeat=repeat))
    assert len(result)==60
    return result

def reserve_attempt(output,job):
    path=Path(os.environ['FLY_COLLISION_BUDGET_LEDGER'])
    if path.parent.resolve()!=output.parent.resolve():raise ValueError('Budget ledger escapes prototype namespace')
    ledger=read(path)
    if ledger['authorization_sha256']!=sha(BASE/'candidate_authorization.json'):
        raise ValueError('Budget authorization changed')
    if len(ledger['attempts'])>=60:raise RuntimeError('TOTAL_APPROVED_ATTEMPT_BUDGET_EXHAUSTED')
    if any(a['job']['id']==job['id'] for a in ledger['attempts']):
        raise RuntimeError('No automatic retry of attempted condition')
    ledger['attempts'].append(dict(job=job,output=str(output),reserved_before_execution=True))
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(ledger,indent=2,allow_nan=False)+'\n');os.replace(temporary,path)
    return len(ledger['attempts'])

def compare_reference(run,scenario,model):
    if model not in ('no_action','circuit','feature_only'):return
    name=f'muniform_population_{scenario}_{model}_r0'
    with np.load(SOURCE_RUN/'episodes'/f'{name}.npz',allow_pickle=False) as saved:
        for key in ('world_times_ms','fly_position','obstacle_positions','speed','frames','frame_timestamps_s',
                    'decision_times_ms','score','sustained_score','escape_event','escape_requested',
                    'controller_states','decision_drive_unscaled','decision_frame_indices','frame_valid'):
            np.testing.assert_array_equal(run['arrays'][key],saved[key])
    meta=read(SOURCE_RUN/'episodes'/f'{name}.json')
    for key in ('first_request_ms','scheduled_actuation_ms','first_motion_ms','turn','failure','end_ms',
                'survived_horizon','escape_success','dangerous_miss','false_alarm','minimum_swept_clearance',
                'final_clearance','path_length'):
        assert run['metrics'][key]==meta['metrics'][key],key

def summarize(results):
    groups={}
    for row in results:
        m=row['metrics'];g=groups.setdefault(row['model'],dict(danger=0,danger_success=0,harmless=0,
            harmless_requests=0,pre_onset_requests=0,physical_failures=0,fallback_events=0,episodes=[]))
        g['danger']+=int(m['danger']);g['danger_success']+=int(m['escape_success'] is True)
        g['harmless']+=int(not m['danger']);g['harmless_requests']+=int(m['false_alarm'])
        g['pre_onset_requests']+=int(m['pre_onset_request']);g['physical_failures']+=int(m['terminated'])
        g['fallback_events']+=m['fallback_events'];g['episodes'].append(dict(id=row['id'],**m))
    for model,g in groups.items():
        g['combined_fixture_target']=None if model=='no_action' else (g['danger']==g['danger_success']==3
            and g['harmless']==2 and g['harmless_requests']==g['pre_onset_requests']==0)
    return groups

def report(output,summary):
    lines=['# Exact-rule bounded prototype result','',
        'One approved analytic candidate; no fitting, threshold search, training or new geometry. Thirty unique combinations and thirty exact repeats on five known development fixtures.',
        'The threat estimate treats the fly as a point. Actual evaluation retains the finite-radius fly; results cannot establish generalization, safe close passing, biological behavior or anatomical superiority.','',
        '| Controller | Danger successes | Harmless requests | Physical failures | Fallbacks | Combined fixture target |',
        '| --- | --- | --- | --- | --- | --- |']
    for model,g in summary['groups'].items():
        target=g['combined_fixture_target'];status='not applicable' if target is None else 'PASS' if target else 'FAIL'
        lines.append(f"| {model} | {g['danger_success']}/{g['danger']} | {g['harmless_requests']}/{g['harmless']} | {g['physical_failures']} | {g['fallback_events']} | {status} |")
    lines+=['','Original control trajectories match their saved v1 counterparts exactly. Internal circuit request, gated physical request, actuation and motion times remain distinct in per-episode records.',
       'A late unknown-perception fallback is still a harmless request and remains in the false-alarm denominator. No policy was retuned or pending circuit initiation erased to improve this table.',
       'The point-observer rule can miss finite-fly collisions on other geometries. Every existing fixture is already development data; none is an independent evaluation family.',
       'The original 120-trial schedule remains paused and incomplete. Existing GRUs were used only by the preserved adapter regression checks, not rerun as additional behavioral conditions.',
       'No independent evaluation, calibration, neural training, dependency installation, commit or push occurred.','']
    (output/'README.md').write_text('\n'.join(lines))

def main():
    if os.environ.get('FLY_COLLISION_SNAPSHOT')!='1':raise ValueError('Use the verified prototype launcher')
    output=Path(os.environ['FLY_COLLISION_OUTPUT']);approved=authorization()
    if output.is_relative_to(ROOT):raise ValueError('Prototype output belongs outside frozen execution snapshot')
    from connectome.scripts.phase7.pipeline import FrozenPipeline
    from connectome.scripts.phase9.config import load_config,fixtures
    started=time.monotonic();pipeline=FrozenPipeline();config=load_config();scenarios=fixtures()
    camera=camera_from_config(config,yaml.safe_load((ROOT/'connectome/phase6/encoder_config.yaml').read_text()))
    legacy=legacy_rows(pipeline);scheduled=jobs(scenarios)
    reference={}
    for s in scenarios:
        for model in ('no_action','circuit','feature_only'):
            ident=f"muniform_population_{s['scenario_id']}_{model}_r0"
            for suffix in ('.json','.npz'):
                name=f'episodes/{ident}{suffix}';reference[name]=sha(SOURCE_RUN/name)
    manifest=dict(protocol=PROTOCOL,status='LOCKED_BEFORE_RULE_CHECKS_AND_PROTOTYPE_EPISODES',
         approval_sha256=sha(BASE/'candidate_authorization.json'),spec_sha256=approved['specification_sha256'],
         stage_a_audit_sha256=approved['stage_a_audit_sha256'],sources_sha256=sources(),
         jobs=scheduled,legacy_controls=legacy,world_config=config,scenarios=scenarios,
         reference_files_sha256=reference,candidate_count=1,calibration_runs=0,threshold_searches=0,
         growth_test='radius_current>radius_previous',closest_approach_boundary=1.,
         boundary_units='object radii, point observer only',persistence_ms=20,motor_command=0.,
         unknown_policy='standalone abstains; pending hybrid falls back immediately',
         limits=dict(total_attempts=60,check_seconds=1800,episode_seconds=900,rss_bytes=4*1024**3,
                     output_plus_snapshot_bytes=1024**3),held_out_authorized=False,training_authorized=False)
    write(output/'manifest.json',manifest)
    with (output/'tests.log').open('w') as log:
        test=subprocess.run([sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider',
            'connectome/scripts/collision_threat_v1/tests','connectome/scripts/collision_threat_v1/tests_prototype',
            'connectome/scripts/behavior_validation/tests',f'--junitxml={output/"tests.xml"}'],
            stdout=log,stderr=subprocess.STDOUT,timeout=max(1,1800-(time.monotonic()-started)))
    if test.returncode:raise RuntimeError('Prototype checks failed before any new episode')
    write(output/'check_gate.json',dict(status='PASS',elapsed_s=time.monotonic()-started,manifest_sha256=sha(output/'manifest.json')))
    runner=PrototypeRunner(pipeline,config,camera,legacy);budget=Budget(output);results=[];timings=[]
    for job in scheduled:
        budget.check();attempt=reserve_attempt(output,job)
        write(output/'progress.json',dict(total_reserved_attempts=attempt,approved_cap=60,current=job))
        begin=time.monotonic()
        try:
            scenario=next(s for s in scenarios if s['scenario_id']==job['scenario'])
            run=runner.run(scenario,job['model'],heartbeat=budget.check)
            compare_reference(run,job['scenario'],job['model'])
            save_episode(output/'episodes',job['id'],run)
            if job['repeat']==1:
                previous=load_episode(output/'episodes',job['id'][:-1]+'0')
                assert run['metrics']==previous['metrics']
                for key in run['arrays']:np.testing.assert_array_equal(run['arrays'][key],previous['arrays'][key])
            else:results.append(dict(**job,metrics=run['metrics']))
            timings.append(dict(id=job['id'],elapsed_s=time.monotonic()-begin))
            write(output/'timings.json',dict(episodes=timings,peak_rss_bytes=rss(),
                 output_bytes=size(output),snapshot_bytes=size(ROOT)))
            print(f"{attempt}/60 {job['id']} {timings[-1]['elapsed_s']:.3f}s",flush=True)
            remaining=60-len(timings)
            if remaining*max(t['elapsed_s'] for t in timings)>900-(time.monotonic()-budget.start):
                raise RuntimeError('Projected remaining episodes exceed approved time budget')
        except BaseException as error:
            write(output/'failure.json',dict(job=job,reserved_attempts=attempt,type=type(error).__name__,
                 error=str(error),traceback=traceback.format_exc(),unresolved=True,
                 completed_unique_episodes=[r['id'] for r in results],no_automatic_retry=True))
            raise
    groups=summarize(results)
    summary=dict(status='COMPLETE_KNOWN_FIXTURE_PROTOTYPE',attempts=len(timings),unique_combinations=len(results),
        exact_repeats_verified=30,groups=groups,elapsed_episode_s=time.monotonic()-budget.start,
        manifest_sha256=sha(output/'manifest.json'),legacy_reference_equivalence_verified=True,
        independent_metric_checks=60,calibration_runs=0,threshold_searches=0,training_runs=0,
        new_world_geometries=0,held_out_evaluations=0,point_observer_limitation=True)
    write(output/'summary.json',summary);report(output,summary)

if __name__=='__main__':
    try:main()
    except BaseException as error:
        if 'FLY_COLLISION_OUTPUT' in os.environ:
            output=Path(os.environ['FLY_COLLISION_OUTPUT'])
            if not (output/'failure.json').exists():
                write(output/'failure.json',dict(type=type(error).__name__,error=str(error),traceback=traceback.format_exc(),
                      prototype_not_completed=True))
        raise
