"""Read-only independent replay of committed train/validation score artifacts.

No neural inference, fitting, held-out evaluation or changes to production files.
The decoder/calibration implementations are deliberately not imported.
"""
import hashlib
import json
import os
from pathlib import Path
import time
import numpy as np

os.nice(10)
ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT/'connectome/Results/phase11/results'
HERE = Path(__file__).parent


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def run():
    start = time.perf_counter()
    rows = read(OUT/'job_ledger.json')
    manifest = {r['scenario_id']:r for r in read(ROOT/'connectome/Results/phase5_5/results/benchmark_manifest.json')['scenarios']}
    reports = []
    checked = 0
    for job in rows:
        if job['status'] != 'COMPLETE' or job['definition']['kind'] != 'calibration':
            continue
        folder = OUT/'calibration'/job['definition']['job_id']
        a = read(folder/'assessments.json')
        freeze = read(folder/'freeze.json')
        expected = freeze.pop('payload_sha256')
        assert digest(freeze) == expected
        assert freeze['calibration'] == a and not freeze['test_inference_authorized']
        assert a['identity']['model_sha256'] in freeze['artifacts_sha256'].values()
        assert not a['test_ids_used'] and not a['smoke_only']
        for name, h in freeze['artifacts_sha256'].items():
            assert sha(ROOT/name) == h, name
        train_ids, val_ids = a['training_ids'], a['validation_ids']
        input_index = read(OUT/'inputs'/str(a['identity']['mapping'])/'index.json')['records']
        assert digest(input_index) == freeze['input_identity']['cache_sha256']
        assert len(train_ids) == 256 and len(val_ids) == 128
        assert not (set(train_ids) & set(val_ids))
        assert not ({manifest[s]['group_id'] for s in train_ids} & {manifest[s]['group_id'] for s in val_ids})
        candidates = a['candidate_plan']['candidates']
        thresholds = np.array([np.inf if c['threshold']['kind']=='always_silent' else c['threshold']['value'] for c in candidates])
        counts = np.zeros((len(candidates), 3), dtype=np.int64)
        negative_maxima = []
        threshold = a['threshold']
        assert json.loads(json.dumps(threshold)) == threshold
        selected_value = np.inf if threshold['kind']=='always_silent' else threshold['value']
        window_counts = {}
        max_clip = 0.
        for split, ids in (('train',train_ids),('validation',val_ids)):
            events = []
            for sid in ids:
                row = manifest[sid]
                assert row['split'] == split and row['cohort'] == split
                p = folder/'scores'/f'{sid}.npz'
                meta = read(p.with_suffix('.json'))
                assert meta['contract']['identity'] == a['identity']
                assert meta['contract']['input_sha256'] == input_index[sid]['sha256']
                assert sha(p) == meta['sha256']
                with np.load(p,allow_pickle=False) as data:
                    score = data['score']
                assert score.dtype == np.float64 and score.shape == (1000,)
                assert np.isfinite(score).all() and (score >= 0).all()
                score_hash = digest(dict(shape=list(score.shape),dtype=str(score.dtype),bytes_sha256=hashlib.sha256(score.tobytes()).hexdigest()))
                assert score_hash == a['score_hashes'][sid]
                # Closed [t-20,t] uses 21 observations. No endpoint t=1000.
                sustained = np.lib.stride_tricks.sliding_window_view(score,21).min(axis=1)
                hit = np.flatnonzero(sustained >= selected_value)
                first = float(hit[0]+20) if hit.size else None
                stored = next(e for e in a['behavior'][split]['per_episode'] if e['scenario_id']==sid)
                assert stored['label'] == row['label'] and stored['role'] == row['role']
                assert stored['first_event_ms'] == first, (sid, first, stored)
                events.append((row['label'], first))
                if split == 'train' and row['label']==0:
                    negative_maxima.append(float(sustained.max()))
                if split == 'validation':
                    above = sustained[None,:] >= thresholds[:,None]
                    any_hit = above.any(axis=1)
                    firsts = np.where(any_hit,above.argmax(axis=1)+20,1000)
                    counts[:,0] += (row['label']==1) & any_hit & (firsts>=200) & (firsts<1000)
                    counts[:,1] += (row['label']==0) & any_hit
                    counts[:,2] += any_hit & (firsts<200)
                max_clip = max(max_clip,meta['diagnostics'].get('clipped_fraction',0.))
                checked += 1
            positives = [(label,t) for label,t in events if label==1]
            negatives = [(label,t) for label,t in events if label==0]
            metrics = dict(timely_tpr=sum(t is not None and 200<=t<1000 for _,t in positives)/len(positives),
                           full_episode_negative_fpr=sum(t is not None for _,t in negatives)/len(negatives),
                           early_alarms=sum(t is not None and t<200 for _,t in events),
                           missed_positives=sum(t is None for _,t in positives))
            for name,value in metrics.items():
                assert a['behavior'][split][name] == value, (folder.name,split,name)
            window_counts[split] = metrics
        raw = np.quantile(np.array(negative_maxima),np.linspace(0.,1.,31))
        expected_values = list(dict.fromkeys(float(np.nextafter(v,np.inf)) for v in raw))
        assert [c['threshold']['value'] for c in candidates if c['threshold']['kind']=='finite'] == expected_values
        assert len(candidates) <= 32 and candidates[-1]['threshold']==dict(kind='always_silent',value=None)
        assert np.array_equal(np.array([[r['timely_tpr']*32,r['full_episode_fpr']*96,r['pre_onset_decisions']] for r in a['assessments']]),counts)
        eligible = [i for i in range(len(candidates)) if counts[i,1]/96 <= .05]
        winner = max(eligible,key=lambda i:(counts[i,0]/32,-counts[i,1]/96,candidates[i]['threshold']['kind']=='always_silent',0. if np.isinf(thresholds[i]) else thresholds[i]))
        assert candidates[winner]['threshold']==threshold
        reports.append(dict(job_id=folder.name,identity=a['identity'],threshold=threshold,metrics=window_counts,
                            freeze_sha256=sha(folder/'freeze.json'),assessment_sha256=sha(folder/'assessments.json'),
                            max_clipped_fraction=max_clip,candidate_count=len(candidates),
                            median_latency_ms=a['behavior']['validation']['median_detected_latency_ms']))
    result = dict(status='PASS',calibration_conditions_checked=len(reports),cached_train_validation_episodes_checked=checked,
                  audit_script_sha256=sha(Path(__file__)),manifest_sha256=sha(ROOT/'connectome/Results/phase5_5/results/benchmark_manifest.json'),
                  runtime_s=time.perf_counter()-start,conditions=reports,
                  scope='Independent replay of cached training/validation scores; no model inference or new threshold conditions.',
                  held_out_inference_runs=0,production_files_modified=0)
    (HERE/'verification.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='conditions'}))


if __name__ == '__main__':
    run()
