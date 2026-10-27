"""Frozen v2 factorial manifest, required tests, then <=80 known-fixture attempts."""
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import numpy as np
import yaml
from .common import ROOT,BASE,PLAN,REFERENCE,PROTOCOL,read,write,sha,sources,rss,size,verify_plan
from .rule import KnownSizePrior
from .driver import ROLES
from .runner import Runner
from .recording import save_episode,load_episode
from connectome.scripts.collision_threat_v1.features import camera_from_config
from connectome.scripts.collision_threat_v1.protocol import legacy_rows
from connectome.scripts.collision_threat_v1.prototype import Budget

REFERENCE_ALIASES={'no_action':'no_action','circuit':'circuit','point_standalone_v1':'closest_approach_rule',
                   'point_original_gate_v1':'circuit_threat_gate'}

def reserve_attempt(output,job):
    path=Path(os.environ['FLY_V2_LEDGER'])
    if path.parent.resolve()!=output.parent.resolve():raise ValueError('Attempt ledger outside run namespace')
    record=read(path)
    if record['authorization_sha256']!=sha(BASE/'authorization.json'):raise ValueError('Attempt authorization changed')
    if len(record['attempts'])>=80:raise RuntimeError('80_ATTEMPT_BUDGET_EXHAUSTED')
    if any(a['job']['episode_id']==job['episode_id'] for a in record['attempts']):raise RuntimeError('No automatic retry')
    record['attempts'].append(dict(job=job,output=str(output),reserved_before_execution=True))
    tmp=path.with_suffix('.tmp');tmp.write_text(__import__('json').dumps(record,indent=2,allow_nan=False)+'\n')
    os.replace(tmp,path);return len(record['attempts'])

def compare_v1(run,job):
    alias=REFERENCE_ALIASES.get(job['controller'])
    if alias is None:return
    path=REFERENCE/'episodes'/f"{job['scenario_id']}_{alias}_r0.npz"
    with np.load(path,allow_pickle=False) as reference:
        for key in ('frames','frame_timestamps_s','world_times_ms','fly_position','obstacle_positions',
                    'speed','score','sustained_score','escape_event','escape_requested','controller_states',
                    'decision_drive_unscaled','decision_frame_indices','frame_valid'):
            np.testing.assert_array_equal(run['arrays'][key],reference[key])
    m=read(path.with_suffix('.json'))['metrics']
    for key in ('first_request_ms','internal_request_ms','physical_request_ms','scheduled_actuation_ms',
                'first_motion_ms','failure','end_ms','survived_horizon','escape_success','false_alarm',
                'minimum_swept_clearance','final_clearance','path_length'):
        assert run['metrics'][key]==m[key],key

def summarize(results):
    groups={}
    for row in results:
        m=row['metrics'];g=groups.setdefault(row['controller'],dict(danger=0,danger_success=0,harmless=0,
            harmless_requests=0,pre_onset=0,physical_failures=0,retirements=0,rearms=0,fallbacks=0,
            unknown_after_retirement_ticks=0,episodes=[]))
        g['danger']+=int(m['danger']);g['danger_success']+=int(m['escape_success'] is True)
        g['harmless']+=int(not m['danger']);g['harmless_requests']+=int(m['false_alarm'])
        g['pre_onset']+=int(m['pre_onset_request']);g['physical_failures']+=int(m['terminated'])
        g['retirements']+=m['retirement_events'];g['rearms']+=m['rearm_events'];g['fallbacks']+=m['fallback_events']
        g['unknown_after_retirement_ticks']+=m['unknown_after_retirement_ticks']
        g['episodes'].append(dict(id=row['episode_id'],**m))
    for name,g in groups.items():
        g['combined_fixture_target']=None if name=='no_action' else (g['danger']==g['danger_success']==3
             and g['harmless']==2 and g['harmless_requests']==g['pre_onset']==0)
    return groups

def report(output,summary):
    lines=['# Known-size finite-body and retirement-gate v2 comparison','',
        'Eight predeclared conditions on five known development fixtures. Forty unique combinations and forty exact repeats; no fitting, threshold search, training, new geometry or independent evaluation.',
        'Finite-body variants receive a declared fixed object-radius prior of 1.5 and self-radius 0.5. Their contact boundary 4/3 is derived, not fitted. This is not unrestricted image-only collision prediction.','',
        '| Controller | Dangerous escapes | Harmless requests | Retirements | Re-arms | Fallbacks | Combined target |',
        '| --- | --- | --- | --- | --- | --- | --- |']
    for name,g in summary['groups'].items():
        target=g['combined_fixture_target'];status='n/a' if target is None else 'PASS' if target else 'FAIL'
        lines.append(f"| {name} | {g['danger_success']}/{g['danger']} | {g['harmless_requests']}/{g['harmless']} | {g['retirements']} | {g['rearms']} | {g['fallbacks']} | {status} |")
    lines+=['','All unchanged v1 conditions match their saved trajectories exactly. Finite-fly swept collision endpoints, causal timing and first physical event semantics remain unchanged.',
        'The known fixtures already pass the point rule, so these outcomes do not establish a finite-body behavioral advantage. Mid-boundary analytic tests check the geometric change; novel physical cases remain unexecuted.',
        'Retiring a request removes its stale unknown fallback; it can also miss a newly dangerous unseen trajectory. Unknown-after-retirement exposure remains in the report and is not treated as certified safety.',
        'Image quantization, known-size assumptions, constant-velocity extrapolation, the growth prerequisite and the one-second horizon remain limitations. No anatomical superiority or biological flight claim follows.',
        'Training remains paused. The original GRU schedule and v1 60-attempt ledger were not resumed or extended. Dashboard files were excluded from scientific preservation scope and not modified.','']
    (output/'README.md').write_text('\n'.join(lines))

def main():
    if os.environ.get('FLY_V2_SNAPSHOT')!='1':raise RuntimeError('Use the verified v2 launcher')
    output=Path(os.environ['FLY_V2_OUTPUT'])
    proposal=verify_plan();approved=read(BASE/'authorization.json')
    if (approved['status']!='USER_APPROVED_IMPLEMENTATION' or approved['plan_sha256']!=sha(PLAN/'README.md')
            or approved['proposed_protocol_sha256']!=sha(PLAN/'proposed_protocol.json')):
        raise ValueError('v2 authorization missing or changed')
    from connectome.scripts.phase7.pipeline import FrozenPipeline
    from connectome.scripts.phase9.config import load_config,fixtures
    start=time.monotonic();pipeline=FrozenPipeline();config=load_config();scenarios=fixtures()
    if config!=proposal['world_config'] or scenarios!=proposal['scenarios']:raise ValueError('World or fixtures differ')
    if list(ROLES)!=[c['id'] for c in proposal['controllers']]:raise ValueError('Controller roster differs')
    prior=KnownSizePrior(proposal['size_information']['object_radius_prior'],proposal['size_information']['self_radius'])
    if prior.contact_radius!=proposal['size_information']['finite_body_contact_radius_normalized']:
        raise ValueError('Prior/boundary mismatch')
    camera=camera_from_config(config,yaml.safe_load((ROOT/'connectome/phase6/encoder_config.yaml').read_text()))
    controls=legacy_rows(pipeline)
    manifest=dict(proposal,execution_protocol=PROTOCOL,status='LOCKED_BEFORE_TESTS_AND_EPISODES',
        approval_sha256=sha(BASE/'authorization.json'),source_hashes=sources(),legacy_controls=controls,
        plan_sha256=sha(PLAN/'README.md'),proposal_sha256=sha(PLAN/'proposed_protocol.json'))
    write(output/'manifest.json',manifest)
    with (output/'tests.log').open('w') as log:
        tests=subprocess.run([sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider',
            'connectome/scripts/collision_threat_v2/tests','connectome/scripts/collision_threat_v1/tests',
            'connectome/scripts/collision_threat_v1/tests_prototype','connectome/scripts/behavior_validation/tests',
            f'--junitxml={output/"tests.xml"}'],stdout=log,stderr=subprocess.STDOUT,
            timeout=max(1,1800-(time.monotonic()-start)))
    if tests.returncode:raise RuntimeError('Required v2/legacy tests failed; no physical episodes permitted')
    write(output/'check_gate.json',dict(status='PASS',elapsed_s=time.monotonic()-start,manifest_sha256=sha(output/'manifest.json')))
    runner=Runner(pipeline,config,camera,controls,prior);budget=Budget(output);results=[];timings=[]
    for job in proposal['jobs']:
        budget.check();attempt=reserve_attempt(output,job)
        write(output/'progress.json',dict(reserved_attempts=attempt,maximum_attempts=80,current=job))
        begun=time.monotonic()
        try:
            scenario=next(s for s in scenarios if s['scenario_id']==job['scenario_id'])
            run=runner.run(scenario,job['controller'],heartbeat=budget.check)
            compare_v1(run,job)
            save_episode(output/'episodes',job['episode_id'],run)
            if job['repeat']==1:
                first=load_episode(output/'episodes',job['episode_id'][:-1]+'0')
                assert first['metrics']==run['metrics']
                for key,value in run['arrays'].items():np.testing.assert_array_equal(value,first['arrays'][key])
            else:results.append(dict(**job,metrics=run['metrics']))
            timings.append(dict(id=job['episode_id'],seconds=time.monotonic()-begun))
            write(output/'timings.json',dict(episodes=timings,peak_rss_bytes=rss(),output_bytes=size(output),snapshot_bytes=size(ROOT)))
            print(f"{attempt}/80 {job['episode_id']} {timings[-1]['seconds']:.3f}s",flush=True)
            if (80-len(timings))*max(t['seconds'] for t in timings)>900-(time.monotonic()-budget.start):
                raise RuntimeError('Projected time budget exceeded')
        except BaseException as error:
            write(output/'failure.json',dict(job=job,reserved_attempts=attempt,error=str(error),
                traceback=traceback.format_exc(),unresolved=True,no_automatic_retry=True))
            raise
    summary=dict(status='COMPLETE_V2_KNOWN_FIXTURE_COMPARISON',attempts=len(timings),unique_combinations=len(results),
        exact_repeats_verified=40,groups=summarize(results),episode_elapsed_s=time.monotonic()-budget.start,
        manifest_sha256=sha(output/'manifest.json'),independent_metric_checks=80,legacy_equivalence_verified=True,
        calibration_runs=0,threshold_searches=0,training_runs=0,new_world_geometries=0,held_out_evaluations=0)
    write(output/'summary.json',summary);report(output,summary)

if __name__=='__main__':
    try:main()
    except BaseException as error:
        if 'FLY_V2_OUTPUT' in os.environ:
            out=Path(os.environ['FLY_V2_OUTPUT'])
            if not (out/'failure.json').exists():write(out/'failure.json',dict(error=str(error),traceback=traceback.format_exc(),comparison_not_completed=True))
        raise
