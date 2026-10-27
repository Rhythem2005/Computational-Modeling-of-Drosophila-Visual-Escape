"""Independent saved-file, gate-timeline and physical-endpoint QA; no new episodes."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
import xml.etree.ElementTree as ET
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
V1=ROOT/'connectome/Results/collision_threat_v1'
REFERENCE=V1/'prototype/1793093607177149000'
ALIASES={'no_action':'no_action','circuit':'circuit','point_standalone_v1':'closest_approach_rule',
         'point_original_gate_v1':'circuit_threat_gate'}
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def verify_retirement(a):
    phase='unarmed';armed=False;retired_at=None;epoch=0;physical_at=None
    for k,state in enumerate(a['rule_state']):
        threat=k>=20 and bool(np.all(a['rule_state'][k-20:k+1]=='threat'))
        clear=k>=20 and bool(np.all(a['rule_state'][k-20:k+1]=='clear_under_model'))
        generated=retired=rearmed=physical=fallback=False
        if a['legacy_escape_requested'][k] and not armed:
            armed=True;phase='pending';epoch=1;generated=True
        if phase=='pending':
            if state=='unknown':physical=True;fallback=True
            elif threat:physical=True
            elif clear:phase='retired_clear';retired_at=k;retired=True
        elif phase=='retired_clear' and threat and k-20>retired_at:
            epoch+=1;generated=True;rearmed=True;physical=True
        if physical:
            assert physical_at is None;physical_at=k;phase='physical_latched'
        for name,value in [('gate_state',phase),('candidate_epoch',epoch),('candidate_generation_event',generated),
              ('retirement_event',retired),('rearm_event',rearmed),('escape_event',physical),
              ('fallback_event',fallback),('current_threat_sustained',threat),('current_clear_sustained',clear),
              ('unknown_after_retirement',phase=='retired_clear' and state=='unknown')]:
            assert a[name][k]==value,(k,name,a[name][k],value)

def main(directory):
    directory=Path(directory).resolve();manifest=read(directory/'manifest.json');summary=read(directory/'summary.json')
    assert summary['status']=='COMPLETE_V2_KNOWN_FIXTURE_COMPARISON'
    assert read(directory/'execution.json')['exit_code']==0
    assert sha(directory/'manifest.json')==summary['manifest_sha256']
    preservation=read(directory/'preservation.json')
    assert preservation['unchanged'] and preservation['active_sources_unchanged']
    before=read(directory/'preservation_before.json');assert before==read(directory/'preservation_after.json')
    assert not any(n.startswith('dashboard/') for n in before)
    for name,h in manifest['source_hashes'].items():assert sha(ROOT/name)==h,name
    assert len(read(directory.parent/'attempt_ledger.json')['attempts'])==80
    assert len(read(V1/'prototype/attempt_ledger.json')['attempts'])==60
    jobs=manifest['jobs'];reserved=read(directory.parent/'attempt_ledger.json')['attempts']
    assert len(jobs)==summary['attempts']==len(reserved)==80
    assert [j['episode_id'] for j in jobs]==[r['job']['episode_id'] for r in reserved]
    assert len(list((directory/'episodes').glob('*.npz')))==len(list((directory/'episodes').glob('*.json')))==80
    tests=list(ET.parse(directory/'tests.xml').getroot().iter('testcase'))
    assert len(tests)==121 and not any(c.find('failure') is not None or c.find('error') is not None or c.find('skipped') is not None for c in tests)
    geometry_source=V1/'audit_prototype.py'
    spec=importlib.util.spec_from_file_location('v1_saved_geometry_checker',geometry_source)
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    bindings={};sensory={};legacy=gate_timelines=0
    for job in jobs:
        ident=job['episode_id'];path=directory/'episodes'/f'{ident}.npz';meta=read(path.with_suffix('.json'))
        assert sha(path)==meta['arrays_sha256']
        with np.load(path,allow_pickle=False) as f:
            assert f['schema_version'].item()=='collision_threat_2.0'
            a={k:f[k].copy() for k in f.files if k!='schema_version'}
        m=meta['metrics'];helper.geometry_check(a,m,meta['config'],meta['scenario'])
        assert m['direct_dn_input_max']==0
        assert int(a['retirement_event'].sum())==m['retirement_events']
        assert int(a['rearm_event'].sum())==m['rearm_events']
        assert a['decision_times_ms'][a['retirement_event']].tolist()==m['retirement_times_ms']
        assert a['decision_times_ms'][a['rearm_event']].tolist()==m['rearm_times_ms']
        assert int(a['unknown_after_retirement'].sum())==m['unknown_after_retirement_ticks']
        if 'retirement_gate' in job['controller']:
            verify_retirement(a);gate_timelines+=1
        if job['controller'].startswith('finite_'):
            assert m['known_size_prior_active'] and m['known_size_prior_matches']
            assert meta['known_size_prior']==dict(object_radius=1.5,self_radius=.5,normalized_contact_radius=4/3)
            assert all(o['radius']==1.5 for o in meta['scenario']['obstacles'])
        else:
            assert not m['known_size_prior_active'] and meta['known_size_prior'] is None
        alias=ALIASES.get(job['controller'])
        if alias:
            reference=REFERENCE/'episodes'/f"{job['scenario_id']}_{alias}_r0.npz"
            with np.load(reference,allow_pickle=False) as f:
                for k in ('frames','score','sustained_score','escape_event','fly_position','obstacle_positions','controller_states'):
                    np.testing.assert_array_equal(a[k],f[k])
            legacy+=1
        if job['repeat']==1:
            first=directory/'episodes'/f'{ident[:-1]}0.npz'
            with np.load(first,allow_pickle=False) as f:
                for k,value in a.items():np.testing.assert_array_equal(value,f[k])
            assert m==read(first.with_suffix('.json'))['metrics']
        else:
            frames=a['frames'];edges=np.concatenate((frames[:,0],frames[:,-1],frames[:,:,0],frames[:,:,-1]),axis=1)
            sensory[ident]=dict(frame_count=len(frames),legacy_valid_frames=int(a['frame_valid'].sum()),
                frame_border_contact=np.any(edges!=meta['config']['background_uint8'],axis=1).tolist(),
                frame_channel_capped=np.any(a['channels']>=1,axis=1).tolist(),
                motion_valid_frames=int(a['measurement_motion_valid'].sum()),
                unknown_decision_ticks=m['unknown_decision_ticks'],unknown_after_retirement_ticks=m['unknown_after_retirement_ticks'],
                fallback_events=m['fallback_events'],all_scheduled_episodes_retained=True)
        bindings[ident]=dict(npz_sha256=sha(path),metadata_sha256=sha(path.with_suffix('.json')))
    proof=read(ROOT/'connectome/Results/finite_body_gate_plan_20261027/evidence_snapshot.json')
    for name,h in proof['production_pointers_sha256'].items():assert sha(ROOT/name)==h
    result=dict(status='PASS_V2_SAVED_FILE_QA',episodes_verified=80,unique_combinations=40,exact_repeats_verified=40,
        tests_verified=121,unchanged_v1_reference_episodes_verified=legacy,
        retirement_gate_timelines_independently_reconstructed=gate_timelines,
        actual_finite_fly_geometry_checked=True,prior_information_separation_checked=True,
        protected_scientific_files=preservation['files'],dashboard_work_excluded=True,
        earlier_v1_budget_unchanged=60,new_v2_budget_consumed=80,production_pointers_unchanged=True,
        new_simulations=0,new_geometry_forecasts=0,new_feature_extraction=0,new_neural_inference=0,
        geometry_checker_sha256=sha(geometry_source),audit_script_sha256=sha(Path(__file__)),
        manifest_sha256=sha(directory/'manifest.json'),episode_files_sha256=bindings,sensory_diagnostics=sensory)
    (directory/'saved_file_audit.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('episode_files_sha256','sensory_diagnostics')}))

if __name__=='__main__':main(sys.argv[1])
