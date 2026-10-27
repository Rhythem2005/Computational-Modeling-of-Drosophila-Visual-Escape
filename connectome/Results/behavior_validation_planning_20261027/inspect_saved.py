"""Planning-only saved-artifact inspection. No model forward calls or dataset loads."""
from pathlib import Path
import collections
import fcntl
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from connectome.scripts.phase11.common import sources, raw_sources

OUT = ROOT / 'connectome/Results/phase11/results'
HERE = Path(__file__).parent

def read(p):
    return json.loads(p.read_text())

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, allow_nan=False).encode()).hexdigest()

def locate(name):
    p = ROOT / name
    if not p.exists():
        p = ROOT / re.sub(r'^connectome/(phase[^/]+)', r'connectome/Results/\1', name)
    return p

def main():
    protected = [OUT/'job_ledger.json', OUT/'execution_continuous.json', OUT/'pause.json',
                 *OUT.glob('training/*/current.json'), *OUT.glob('selected/*/*'),
                 *OUT.glob('calibration/*/freeze.json')]
    before = {str(p.relative_to(ROOT)): sha(p) for p in protected if p.is_file()}
    with (OUT/'manual_worker.lock').open('r') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(lock, fcntl.LOCK_UN)
    rows = read(OUT/'job_ledger.json')
    jobs = {r['definition']['job_id']: r for r in rows}
    complete = [r for r in rows if r['status'] == 'COMPLETE']
    checkpoints = []
    for p in sorted(OUT.glob('training/*/current.json')):
        c = read(p); payload = c.pop('payload_sha256')
        assert digest(c) == payload
        assert sha(p.parent/c['arrays_file']) == c['arrays_sha256']
        checkpoints.append(dict(job_id=p.parent.name, epoch=c['epoch'], offset=c['offset'],
                                updates=c['adam_updates'], finished=c['finished']))
    trials = {}
    for r in complete:
        d = r['definition']
        if d['kind'] != 'gru_trial':
            continue
        folder = OUT/'training'/d['job_id']; report = read(folder/'report.json')
        current = read(folder/'current.json')
        assert current['finished'] and not report['smoke_only']
        assert sha(folder/'selected.npz') == report['parameters_sha256'] == r['parameters_sha256']
        assert report['history'] == current['history']
        assert report['best_epoch'] == current['best_epoch']
        assert report['validation_bce'] == current['best_bce']
        assert report['updates'] == current['adam_updates']
        best = min(report['history'], key=lambda x: x['validation_bce'])
        assert best['epoch'] == report['best_epoch'] and best['validation_bce'] == report['validation_bce']
        trials[d['job_id']] = report
    selected = []
    uncalibrated = []
    effective_sources = sources()  # Enforces the existing exact operational compatibility certificate.
    for p in sorted(OUT.glob('selected/*/*.json')):
        s = read(p); mapping = s['mapping']; seed = s['seed']
        assert s['status'] == 'TRAIN_VALIDATION_SELECTED'
        candidates = [trials[f'train_{mapping}_{seed}_{rate}'] for rate in ('0p0003', '0p001')]
        assert s['training']['candidates'] == candidates and not s['training']['failed_trials']
        best = min(candidates, key=lambda x: (x['validation_bce'], x['learning_rate']))
        assert s['training']['selected'] == best
        assert sha(p.with_suffix('.npz')) == s['parameters_sha256'] == best['parameters_sha256']
        key = f'cal_{mapping}_gru_{seed}'
        if jobs[key]['status'] != 'COMPLETE':
            uncalibrated.append(dict(mapping=mapping, seed=seed, status=jobs[key]['status'],
                                     eligibility='EXCLUDE: selection verified, completed calibration absent'))
            continue
        freeze_path = OUT/'calibration'/key/'freeze.json'
        f = read(freeze_path); payload = f.pop('payload_sha256')
        assert digest(f) == payload and f['phase11_sources_sha256'] == effective_sources
        assert f['test_inference_authorized'] is False
        cal = f['calibration']
        assert not cal['smoke_only'] and not cal['test_ids_used']
        assert cal['identity']['model_sha256'] == s['parameters_sha256']
        assert str(cal['identity']['mapping']) == str(mapping)
        assert cal['training_ids'] == best['training_ids'] and cal['validation_ids'] == best['validation_ids']
        for name, h in f['artifacts_sha256'].items():
            assert sha(locate(name)) == h, name
        for field, name in [('manifest_sha256','connectome/phase5_5/results/benchmark_manifest.json'),
                            ('phase10_lock_sha256','connectome/Results/phase10/results/definition_lock.json'),
                            ('phase10_artifact_index_sha256','connectome/Results/phase10/results/delivery_artifact_index.json')]:
            assert sha(locate(name)) == f[field]
        selected.append(dict(mapping=mapping, seed=seed, threshold=cal['threshold'],
                             selected_learning_rate=best['learning_rate'], parameters_sha256=s['parameters_sha256'],
                             freeze=str(freeze_path.relative_to(ROOT)), freeze_sha256=sha(freeze_path),
                             eligibility='saved selection/calibration chain verified; behavioral adapter not implemented'))
    assert before == {name: sha(ROOT/name) for name in before}
    result = dict(status='PASS_SAVED_ARTIFACT_INSPECTION', date_local='2026-10-27',
                  training_complete=len(trials), calibration_complete=sum(r['definition']['kind']=='calibration' for r in complete),
                  selected_records=len(selected)+len(uncalibrated), selected_grus=len(selected),
                  selected_by_mapping=dict(collections.Counter(str(r['mapping']) for r in selected)),
                  selected_without_completed_calibration=uncalibrated,
                  partial=[r for r in checkpoints if not r['finished']], checkpoints_checked=len(checkpoints),
                  worker_lease_available_at_check=True, production_pointers_and_frozen_records_unchanged=True,
                  execution_record=read(OUT/'execution_continuous.json'), pause_record=read(OUT/'pause.json'),
                  process_observation='Separate ps inventory: no Phase 9/11 worker observed; point-in-time check only.',
                  neural_inference_runs=0, simulations=0, test_suites=0, held_out_evaluations=0,
                  scope='Hash/JSON metadata verification; no NPZ numerical replay or full source-contract restoration.',
                  script_sha256=sha(Path(__file__)), execution_sources_sha256=raw_sources(),
                  protected_sha256=before, selected=selected)
    (HERE/'saved_state_verification.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ('status','training_complete','calibration_complete','selected_grus','selected_by_mapping','partial')}))

if __name__ == '__main__':
    main()
