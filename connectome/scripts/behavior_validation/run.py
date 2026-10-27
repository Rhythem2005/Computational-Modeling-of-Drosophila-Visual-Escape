"""Freeze manifest, gate targeted checks, then run <=182 approved fixture attempts."""
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import traceback
import numpy as np
from .common import ROOT, PROTOCOL, Budget, read, write, sources, sha, rss, size
from .artifacts import load_roster, public_roster
from .runner import Runner
from .evidence import save_episode, load_episode

def manifest(roster,config,scenarios):
    jobs=[]
    for mapping, rows in roster.items():
        cases=scenarios if mapping=='uniform_population' else [s for s in scenarios if s['scenario_id'] in ('world_left','world_right')]
        for s in cases:
            for row in rows:
                for repeat in (0,1):
                    jobs.append(dict(episode_id=f"m{mapping}_{s['scenario_id']}_{row['id']}_r{repeat}",
                                mapping=mapping, scenario_id=s['scenario_id'], model_id=row['id'],repeat=repeat))
    assert len(jobs)==182
    return dict(protocol=PROTOCOL,status='LOCKED_BEFORE_ENGINEERING_CHECKS_AND_NEW_BEHAVIOR',
                roster=public_roster(roster), world_config=config, scenarios=scenarios, jobs=jobs,
                source_hashes=sources(), motor_command=0.0, trained_gru_coverage='20/60 selected/calibrated; full schedule incomplete',
                no_new_thresholds=True,no_new_seeds=True,no_new_geometries=True,
                held_out_authorized=False,world_calibration_authorized=False,
                acceptance='primary active controller: 3/3 danger success, 0/2 harmless requests, no pre-onset requests',
                limits=dict(episodes=182,rss_bytes=4*1024**3,output_and_snapshot_bytes=2*1024**3,
                            check_seconds=1800,behavior_seconds=3600))

def main():
    if os.environ.get('FLY_BEHAVIOR_SNAPSHOT')!='1':
        raise RuntimeError('Use the verified snapshot launcher')
    output=Path(os.environ['FLY_BEHAVIOR_OUTPUT'])
    if output.is_relative_to(ROOT):
        raise ValueError('Outputs must be outside protected execution snapshot')
    from connectome.scripts.phase7.pipeline import FrozenPipeline
    from connectome.scripts.phase9.config import load_config,fixtures
    checks_started=time.monotonic()
    pipeline=FrozenPipeline();roster=load_roster(pipeline);config=load_config();scenarios=fixtures()
    plan=manifest(roster,config,scenarios)
    write(output/'manifest.json',plan)
    with (output/'checks.log').open('w') as log:
        result=subprocess.run([sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider',
                 'connectome/scripts/behavior_validation/tests',f'--junitxml={output/"checks.xml"}'],
                 stdout=log,stderr=subprocess.STDOUT,timeout=max(1,1800-(time.monotonic()-checks_started)))
    if result.returncode:
        raise RuntimeError('Adapter checks failed; behavior blocked; see checks.log')
    write(output/'check_gate.json',dict(status='PASS',elapsed_s=time.monotonic()-checks_started,
          manifest_sha256=sha(output/'manifest.json')))
    budget=Budget(output,3600)
    runner=Runner(pipeline,config)
    results=[];timing={};coupling={}
    for job in plan['jobs']:
        budget.begin_episode()
        write(output/'progress.json',dict(attempts=budget.attempts,total=182,current=job))
        before=time.monotonic()
        row=next(r for r in roster[job['mapping']] if r['id']==job['model_id'])
        scenario=next(s for s in scenarios if s['scenario_id']==job['scenario_id'])
        try:
            run=runner.run(scenario,job['mapping'],row,heartbeat=lambda: heartbeat(budget))
            record=save_episode(output/'episodes',job['episode_id'],run)
            if job['repeat']==1:
                first=load_episode(output/'episodes',job['episode_id'][:-1]+'0')
                assert first['metrics']==run['metrics']
                for key,value in run['arrays'].items():
                    np.testing.assert_array_equal(first['arrays'][key],value)
            if job['mapping']=='uniform_population' and row['model']=='circuit':
                compare_legacy(scenario,run)
            if job['repeat']==0:
                results.append(dict(**job,metrics=run['metrics']))
                if job['mapping']=='uniform_population' and job['scenario_id']=='world_head_on':
                    coupling[row['id']]=job['episode_id']
            elapsed=time.monotonic()-before
            timing.setdefault(row['model'],[]).append(elapsed)
            write(output/'timings.json',dict(per_controller_s=timing,peak_rss_bytes=rss(),
                  artifact_bytes=size(output),snapshot_bytes=size(ROOT)))
            print(f"{budget.attempts}/182 {job['episode_id']} {elapsed:.3f}s",flush=True)
            remaining=plan['jobs'][budget.attempts:]
            projected=sum(max(timing.get(next(r['model'] for r in roster[j['mapping']] if r['id']==j['model_id']),
                                [max(v for times in timing.values() for v in times)])) for j in remaining)
            if projected > budget.seconds-(time.monotonic()-budget.started):
                raise RuntimeError('Projected completion exceeds behavior wall budget')
        except BaseException as error:
            write(output/'failure.json',dict(job=job,attempts=budget.attempts,type=type(error).__name__,
                  error=str(error),traceback=traceback.format_exc(),unresolved=True,
                  successful_unique_episodes=[r['episode_id'] for r in results],
                  note='No automatic retry, seed replacement, retuning, or invented physical outcome.'))
            raise
    coupling_check(output,coupling)
    summary=make_summary(results)
    summary.update(status='COMPLETE_ENGINEERING',attempts=budget.attempts,unique_episodes=len(results),
                   exact_repeats_verified=91,behavior_elapsed_s=time.monotonic()-budget.started,
                   manifest_sha256=sha(output/'manifest.json'),all_metrics_independently_checked=True,
                   held_out_evaluations=0,training_runs=0,calibration_runs=0,new_behavioral_geometries=0)
    write(output/'summary.json',summary)
    report(output,summary)

def heartbeat(budget):
    budget.check()
    from connectome.scripts.phase11.runtime import thermal
    t=thermal()
    if t['available'] and t['state']>=2:
        raise RuntimeError('SERIOUS_OR_CRITICAL_THERMAL_PRESSURE')

def compare_legacy(scenario,run):
    name=scenario['scenario_id']+'_primary'
    with np.load(ROOT/f'connectome/phase9/results/episodes/{name}.npz',allow_pickle=False) as f:
        for new,old in [('controller_states','states'),('score','score'),('fly_position','fly_position'),
                        ('obstacle_positions','obstacle_positions'),('frames','frames'),
                        ('escape_event','escape_event'),('frame_valid','frame_valid')]:
            np.testing.assert_array_equal(run['arrays'][new],f[old])

def coupling_check(output,episodes):
    active=load_episode(output/'episodes',episodes['circuit'])
    idle=load_episode(output/'episodes',episodes['no_action'])
    a,b=active['arrays'],idle['arrays']
    first_motion=active['metrics']['first_motion_ms']/1000
    n=min(len(a['frames']),len(b['frames']))
    pre=a['frame_timestamps_s'][:n]<=first_motion
    np.testing.assert_array_equal(a['frames'][:n][pre],b['frames'][:n][pre])
    changed=np.count_nonzero(a['frames'][:n][~pre]!=b['frames'][:n][~pre])
    assert changed>0
    write(output/'coupling.json',dict(equal_pre_motion_frames=True,post_motion_changed_pixels=int(changed),
          note='Actual controller versus no-action feedback; unequal later observations are expected.'))

def make_summary(results):
    groups={}
    for row in results:
        key=row['mapping']+'/'+row['model_id'];m=row['metrics']
        group=groups.setdefault(key,dict(danger=0,danger_success=0,harmless=0,false_alarms=0,pre_onset=0,
                                       physical_failures=0,fully_valid_episodes=0,episodes=[]))
        group['danger']+=int(m['danger']);group['danger_success']+=int(m['escape_success'] is True)
        group['harmless']+=int(not m['danger']);group['false_alarms']+=int(m['false_alarm'])
        group['pre_onset']+=int(m['pre_onset_request']);group['physical_failures']+=int(m['terminated'])
        group['fully_valid_episodes']+=int(m['whole_episode_encoder_valid'])
        group['episodes'].append(dict(id=row['episode_id'],**m))
    for key,g in groups.items():
        g['combined_primary_fixture_target']=None if not key.startswith('uniform_population/') or key.endswith('/no_action') else (
            g['danger']==g['danger_success']==3 and g['harmless']==2 and g['false_alarms']==g['pre_onset']==0)
    return dict(groups=groups,full_gru_schedule_incomplete=True,eligible_grus=20,planned_full_selected_grus=60,
                independent_world_geometries=0,known_fixture_geometries=5,
                secondary_harmless_coverage=0,interpretation='Known engineering fixtures only; no generalization or biological claim.')

def report(output,summary):
    lines=['# Behavioral engineering comparison v1','',
           'Adapters and numerical/causal checks passed. Completed 91 unique fixture/controller combinations and 91 exact repeats.',
           'These are five known geometries, not 182 independent threats. Frozen open-loop thresholds were reused without world calibration.','',
           '| Mapping / model | Danger success | Harmless requests | Physical failures | Fully valid episodes | Combined primary target |',
           '| --- | --- | --- | --- | --- | --- |']
    for key,g in summary['groups'].items():
        target=g['combined_primary_fixture_target']
        lines.append(f"| {key} | {g['danger_success']}/{g['danger']} | {g['false_alarms']}/{g['harmless']} | {g['physical_failures']} | {g['fully_valid_episodes']}/{len(g['episodes'])} | {'not applicable' if target is None else 'PASS' if target else 'FAIL'} |")
    lines += ['', 'The full GRU schedule remains incomplete: 20/60 selected-and-calibrated models were used; two selected but uncalibrated models and the partial trial remain excluded.',
              'Secondary mapping 55010 has only left/right dangerous fixtures and no harmless coverage. No favorable seed or threshold was selected.',
              'Per-episode onset/request/motion timing, swept/final clearance, collisions, movement cost, sensory validity and input-domain limitations are in summary.json and episode records.',
              'The engineering gate establishes implementation consistency. Combined behavioral failures remain failures; no tuning or new conditions were introduced to rescue them.',
              'No training, calibration, held-out evaluation, dependency installation, commit or push occurred. Biological flight, permanent safety and anatomical superiority remain unestablished.','']
    (output/'README.md').write_text('\n'.join(lines))

if __name__=='__main__':
    try:main()
    except BaseException as error:
        if 'FLY_BEHAVIOR_OUTPUT' in os.environ:
            output=Path(os.environ['FLY_BEHAVIOR_OUTPUT'])
            if not (output/'failure.json').exists():
                write(output/'failure.json',dict(type=type(error).__name__,error=str(error),traceback=traceback.format_exc(),
                      behavior_not_completed=True))
        raise
