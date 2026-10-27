"""Read-only verification of existing Phase 9 evidence; no simulation or fitting."""
from pathlib import Path
import fcntl
import hashlib
import json
import re
import xml.etree.ElementTree as ET
import numpy as np

ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT/'connectome/Results/phase9'
RESULTS = BASE/'results'
HERE = Path(__file__).parent


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def locate(name):
    p = ROOT/name
    if not p.exists():
        p = ROOT/re.sub(r'^connectome/(phase[^/]+)',r'connectome/Results/\1',name)
    return p


def run():
    production = ROOT/'connectome/Results/phase11/results'
    pointers = [production/'job_ledger.json', *production.glob('training/*/current.json')]
    before = {str(p):sha(p) for p in pointers}
    with (production/'manual_worker.lock').open('r') as f:
        fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        fcntl.flock(f,fcntl.LOCK_UN)
    lock = read(RESULTS/'definition_lock.json')
    sources = lock['sources_sha256']
    for name,h in sources.items():
        assert sha(locate(name)) == h, name
    artifacts = read(RESULTS/'delivery_artifact_index.json')
    for name,h in artifacts.items():
        assert sha(locate(name)) == h, name
    episodes = []
    for meta_path in sorted((RESULTS/'episodes').glob('*_metadata.json')):
        episode_id = meta_path.name.removesuffix('_metadata.json')
        metadata = read(meta_path)
        for name,h in metadata['files_sha256'].items():
            assert Path(name).name == name and sha(meta_path.parent/name)==h
        config = read(meta_path.parent/f'{episode_id}_config.json')
        metrics = read(meta_path.parent/f'{episode_id}_metrics.json')
        with np.load(meta_path.parent/f'{episode_id}.npz',allow_pickle=False) as d:
            t,fly,obs = d['world_times_ms'],d['fly_position'],d['obstacle_positions']
            assert np.isfinite(fly).all() and np.isfinite(obs).all()
            radii = np.array([ob['radius'] for ob in config['scenario']['obstacles']])+config['world']['fly_radius']
            relative = obs-fly[:,None,:]
            p,delta = relative[:-1],np.diff(relative,axis=0)
            norm = np.sum(delta*delta,axis=-1)
            alpha = np.divide(-np.sum(p*delta,axis=-1),norm,out=np.zeros_like(norm),where=norm>0)
            closest = p+np.clip(alpha,0,1)[...,None]*delta
            minimum = float((np.linalg.norm(closest,axis=-1)-radii).min())
            final = float((np.linalg.norm(relative[-1],axis=-1)-radii).min())
            displacement = np.linalg.norm(np.diff(fly,axis=0),axis=-1)
            path_length = float(displacement.sum())
            moves = np.flatnonzero(displacement>0)
            first_motion = None if not moves.size else float(t[moves[0]])
            event_indices = np.flatnonzero(d['escape_event'])
            assert len(event_indices)<=1
            first_request = None if not event_indices.size else float(d['decision_times_ms'][event_indices[0]])
            assert first_request == metrics['first_request_ms']
            assert first_motion == metrics['first_motion_ms']
            assert np.isclose(minimum,metrics['minimum_swept_clearance'],atol=1e-12,rtol=1e-12)
            assert np.isclose(final,metrics['final_clearance'],atol=1e-12,rtol=1e-12)
            assert np.isclose(path_length,metrics['path_length'],atol=1e-12,rtol=1e-12)
            assert np.mean(d['frame_valid'])==metrics['encoder_valid_fraction']
            assert t[-1]==metrics['end_ms']
            if first_request is not None:
                assert metrics['scheduled_actuation_ms']==first_request+config['world']['actuation_delay_ms']
                assert first_motion is None or first_motion>=metrics['scheduled_actuation_ms']
            survived = minimum>0 and t[-1]==config['world']['duration_ms'] and not metrics['terminated']
            assert survived==metrics['survived_horizon']
            # Independently solve the stationary-fly contact quadratic.
            contacts=[]
            onset=config['world']['obstacle_motion_onset_ms']
            duration=(config['world']['duration_ms']-onset)/1000
            for ob,radius in zip(config['scenario']['obstacles'],radii):
                origin=np.array(ob['position'])-config['scenario']['fly_position']
                velocity=np.array(ob['velocity'])
                aa=float(velocity@velocity);bb=2*float(origin@velocity);cc=float(origin@origin-radius**2)
                if cc<=0:contacts.append(0.)
                elif aa>0 and bb*bb-4*aa*cc>=0:
                    entry=(-bb-np.sqrt(bb*bb-4*aa*cc))/(2*aa)
                    if 0<=entry<=duration:contacts.append(onset+entry*1000)
            danger=bool(contacts)
            assert danger==metrics['danger']
            if danger:assert np.isclose(min(contacts),metrics['stationary_contact_ms'])
            expected_success=None if not danger else bool(first_request is not None and first_request<min(contacts) and survived and final>=config['world']['success_final_clearance_min'])
            assert expected_success==metrics['escape_success']
            assert (not danger and first_request is not None)==metrics['false_alarm']
        episodes.append(dict(episode_id=episode_id,**metrics))
    assert len(episodes)==15
    delivery=read(RESULTS/'delivery_verification.json')
    cases=list(ET.parse(RESULTS/'tests.xml').getroot().iter('testcase'))
    assert len(cases)==28 and not any(c.find('failure') is not None or c.find('error') is not None for c in cases)
    assert before=={str(p):sha(p) for p in pointers}
    ledger=read(production/'job_ledger.json')
    result=dict(status='PASS',phase9_source_hashes_verified=len(sources),phase9_artifact_hashes_verified=len(artifacts),
                saved_episodes_independently_checked=len(episodes),dangerous_fixtures=sum(e['danger'] for e in episodes),
                successful_dangerous_fixtures=sum(e['escape_success'] is True for e in episodes),
                harmless_fixture_false_alarms=[e['episode_id'] for e in episodes if e['false_alarm']],
                encoder_valid_fraction_range=[min(e['encoder_valid_fraction'] for e in episodes),max(e['encoder_valid_fraction'] for e in episodes)],
                existing_phase9_xml_tests_verified=len(cases),new_tests_or_behavioral_runs_executed=0,
                historical_total_tests_reported=delivery['unique_tests_passed'],historical_integration_assertions_reported=delivery['phase4_integration_assertions_passed'],
                training_complete=sum(r['status']=='COMPLETE' and r['definition']['kind']=='gru_trial' for r in ledger),
                calibration_complete=sum(r['status']=='COMPLETE' and r['definition']['kind']=='calibration' for r in ledger),
                production_ledger_and_checkpoint_pointers_unchanged=True,training_remains_paused=True,
                held_out_inference_runs=0,script_sha256=sha(Path(__file__)),episodes=episodes)
    (HERE/'verification.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='episodes'}))


if __name__=='__main__':
    run()
