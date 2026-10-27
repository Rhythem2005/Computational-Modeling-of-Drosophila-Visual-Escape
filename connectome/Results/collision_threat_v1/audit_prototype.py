"""Saved-prototype QA only. No new rule scoring, feature extraction or simulations."""
from pathlib import Path
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
import numpy as np

ROOT=Path(__file__).resolve().parents[3]

def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def geometry_check(a,m,config,scenario):
    relative=a['obstacle_positions']-a['fly_position'][:,None,:]
    radii=np.array([ob['radius'] for ob in scenario['obstacles']])+config['fly_radius']
    p=relative[:-1];d=np.diff(relative,axis=0);norm=(d*d).sum(-1)
    q=np.divide(-(p*d).sum(-1),norm,out=np.zeros_like(norm),where=norm>0)
    closest=p+np.clip(q,0,1)[...,None]*d
    minimum=float((np.linalg.norm(closest,axis=-1)-radii).min())
    final=float((np.linalg.norm(relative[-1],axis=-1)-radii).min())
    assert np.isclose(minimum,m['minimum_swept_clearance'],atol=1e-12,rtol=1e-12)
    assert np.isclose(final,m['final_clearance'],atol=1e-12,rtol=1e-12)
    displacement=np.linalg.norm(np.diff(a['fly_position'],axis=0),axis=-1)
    assert np.isclose(displacement.sum(),m['path_length'],atol=1e-12,rtol=1e-12)
    motions=np.flatnonzero(displacement>0)
    motion=None if not len(motions) else float(a['world_times_ms'][motions[0]])
    events=np.flatnonzero(a['escape_event']);assert len(events)<=1
    request=None if not len(events) else float(a['decision_times_ms'][events[0]])
    assert request==m['first_request_ms']==m['physical_request_ms']
    assert motion==m['first_motion_ms']
    if request is not None:
        assert m['scheduled_actuation_ms']==request+20
        assert motion is None or motion>=m['scheduled_actuation_ms']
    contacts=[]
    for ob,radius in zip(scenario['obstacles'],radii):
        origin=np.array(ob['position'])-scenario['fly_position'];v=np.array(ob['velocity'])
        aa=float(v@v);bb=float(2*origin@v);cc=float(origin@origin-radius**2)
        if cc<=0:contacts.append(0.)
        elif aa>0 and bb*bb-4*aa*cc>=0:
            t=(-bb-np.sqrt(bb*bb-4*aa*cc))/(2*aa)
            if 0<=t<=(1000-config['obstacle_motion_onset_ms'])/1000:
                contacts.append(config['obstacle_motion_onset_ms']+t*1000)
    assert bool(contacts)==m['danger']
    if contacts:assert np.isclose(min(contacts),m['stationary_contact_ms'])
    bounds=np.array(config['bounds_xy'])+np.array([config['fly_radius'],-config['fly_radius']])
    inside=bool(np.all(a['fly_position']>bounds[:,0]) and np.all(a['fly_position']<bounds[:,1]))
    survived=bool(minimum>0 and inside and a['world_times_ms'][-1]==1000 and not m['terminated'])
    assert survived==m['survived_horizon']
    success=None if not contacts else bool(request is not None and request<min(contacts) and survived and final>=1)
    assert success==m['escape_success']
    assert bool(not contacts and request is not None)==m['false_alarm']
    assert a['decision_times_ms'][-1]<min(1000,a['world_times_ms'][-1])
    assert len(a['controller_states'])==int(a['world_times_ms'][-1])+1
    assert np.isfinite(a['controller_states']).all()
    np.testing.assert_array_equal(a['decision_frame_indices'],
        np.searchsorted(a['frame_timestamps_s'],a['decision_times_ms']/1000,side='right')-1)

def main(directory):
    directory=Path(directory).resolve();manifest=read(directory/'manifest.json');summary=read(directory/'summary.json')
    assert read(directory/'execution.json')['exit_code']==0
    assert summary['status']=='COMPLETE_KNOWN_FIXTURE_PROTOTYPE'
    assert summary['manifest_sha256']==sha(directory/'manifest.json')
    preservation=read(directory/'preservation.json')
    assert preservation['unchanged'] and preservation['stage_a_unchanged'] and preservation['active_sources_unchanged']
    assert read(directory/'preservation_before.json')==read(directory/'preservation_after.json')
    assert read(directory/'stage_a_preservation_before.json')==read(directory/'stage_a_preservation_after.json')
    tests=list(ET.parse(directory/'tests.xml').getroot().iter('testcase'))
    assert len(tests)==73 and not any(c.find('failure') is not None or c.find('error') is not None or c.find('skipped') is not None for c in tests)
    for name,h in manifest['sources_sha256'].items():assert sha(ROOT/name)==h
    for name,h in manifest['reference_files_sha256'].items():
        assert sha(ROOT/'connectome/Results/behavior_validation/1793090166386522000'/name)==h
    ledger=read(directory.parent/'attempt_ledger.json')
    assert len(ledger['attempts'])==60==len(manifest['jobs'])==summary['attempts']
    assert len(list((directory/'episodes').glob('*.npz')))==60
    assert len(list((directory/'episodes').glob('*.json')))==60
    for expected,actual in zip(manifest['jobs'],ledger['attempts']):assert expected==actual['job']
    sensory={};hashes={};legacy_equal=0
    for job in manifest['jobs']:
        path=directory/'episodes'/f"{job['id']}.npz";meta=read(path.with_suffix('.json'))
        assert sha(path)==meta['arrays_sha256']
        hashes[job['id']]=dict(npz_sha256=sha(path),metadata_sha256=sha(path.with_suffix('.json')))
        with np.load(path,allow_pickle=False) as data:
            assert data['schema_version'].item()=='collision_threat_1.0'
            a={k:data[k].copy() for k in data.files if k!='schema_version'}
        geometry_check(a,meta['metrics'],meta['config'],meta['scenario'])
        if job['repeat']==1:
            first_path=directory/'episodes'/f"{job['id'][:-1]}0.npz"
            with np.load(first_path,allow_pickle=False) as first:
                for key,value in a.items():np.testing.assert_array_equal(value,first[key])
            assert meta['metrics']==read(first_path.with_suffix('.json'))['metrics']
        if job['model'] in ('no_action','circuit','feature_only'):
            original=ROOT/'connectome/Results/behavior_validation/1793090166386522000/episodes'/f"muniform_population_{job['scenario']}_{job['model']}_r0.npz"
            with np.load(original,allow_pickle=False) as old:
                for key in ('frames','fly_position','obstacle_positions','score','sustained_score','escape_event','controller_states'):
                    np.testing.assert_array_equal(a[key],old[key])
            legacy_equal+=1
        internal=np.flatnonzero(a['legacy_escape_event'])
        assert len(internal)<=1
        first_internal=None if not len(internal) else float(a['decision_times_ms'][internal[0]])
        assert first_internal==meta['metrics']['internal_request_ms']
        assert int(a['fallback_event'].sum())==meta['metrics']['fallback_events']
        if job['model']=='circuit_threat_gate':
            assert first_internal is None or meta['metrics']['first_request_ms'] is None or meta['metrics']['first_request_ms']>=first_internal
            for k in np.flatnonzero(a['fallback_event']):assert a['rule_state'][k]=='unknown' and a['legacy_escape_requested'][k]
        if job['repeat']==0:
            frames=a['frames'];border=np.concatenate((frames[:,0],frames[:,-1],frames[:,:,0],frames[:,:,-1]),axis=1)
            clipped=np.any(border!=meta['config']['background_uint8'],axis=1)
            cap=np.any(a['channels']>=1,axis=1)
            sensory[job['id']]=dict(frame_count=len(frames),legacy_valid_frames=int(a['frame_valid'].sum()),
                 frame_clipped=clipped.tolist(),frame_channel_capped=cap.tolist(),
                 measurement_frames=len(a['measurement_timestamps_s']),measurement_valid_frames=int(a['measurement_measurement_valid'].sum()),
                 motion_valid_frames=int(a['measurement_motion_valid'].sum()),
                 unknown_decision_ticks=int(np.count_nonzero(a['rule_state']=='unknown')),
                 fallback_events=meta['metrics']['fallback_events'],all_episodes_included=True)
    snapshot=read(ROOT/'connectome/Results/collision_threat_implementation_plan_20261027/evidence_snapshot.json')
    for name,h in snapshot['production_pointers_sha256'].items():assert sha(ROOT/name)==h
    result=dict(status='PASS_SAVED_PROTOTYPE_QA',episodes_verified=60,unique_combinations=30,exact_repeats_verified=30,
       test_cases_verified=73,legacy_reference_episodes_exact=legacy_equal,
       preserved_original_files=preservation['files'],preserved_stage_a_files=preservation['stage_a_files'],
       actual_finite_fly_geometry_independently_checked=True,internal_physical_timing_independently_checked=True,
       ledger_and_partial_checkpoint_unchanged=True,approved_attempt_budget_consumed=60,
       new_simulations=0,new_rule_scoring=0,new_model_inference=0,new_feature_extraction=0,
       audit_script_sha256=sha(Path(__file__)),manifest_sha256=sha(directory/'manifest.json'),
       episode_files_sha256=hashes,sensory_diagnostics=sensory)
    (directory/'saved_file_audit.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('episode_files_sha256','sensory_diagnostics')}))

if __name__=='__main__':main(sys.argv[1])
