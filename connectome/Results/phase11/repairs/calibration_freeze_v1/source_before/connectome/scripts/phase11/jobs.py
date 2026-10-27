"""Exact registered job ledger and checked Phase 11-only freeze artifacts."""
from pathlib import Path
import traceback
import numpy as np
from connectome.scripts.phase10.common import config
from connectome.scripts.phase10.data import validate_coverage
from connectome.scripts.phase10.models import freeze_identity, score_model, rate_trace, minimal_features
from connectome.scripts.phase10.networks import load_network
from connectome.scripts.phase10.gru import GRU
from connectome.scripts.phase8.completion.controls import fit_linear
from .common import ROOT, OUT, read, write, arrays, sha, digest, sources
from .training import train_trial
from .assessment import assess
from .dataset import Dataset


def schedule():
    plan = read(ROOT/'connectome/Results/phase10/results/benchmark_job_plan.json')
    jobs = []
    for row in plan['gru_training']:
        for rate in row['rates']:
            jobs.append(dict(job_id=f"train_{row['mapping']}_{row['seed']}_{str(rate).replace('.', 'p')}",
                 kind='gru_trial', mapping=row['mapping'], seed=row['seed'], rate=rate))
        jobs.append(dict(job_id=f"cal_{row['mapping']}_gru_{row['seed']}", kind='calibration',
                 model_id='gru', mapping=row['mapping'], seed=row['seed']))
    for row in plan['rate_models']:
        jobs.append(dict(job_id=f"cal_{row['mapping']}_{row['model_id']}_{row['condition']}",
             kind='calibration', **row))
    for row in plan['minimal_controls']:
        jobs.append(dict(job_id=f"cal_{row['mapping']}_{row['model_id']}", kind='calibration', **row))
    if len({r['job_id'] for r in jobs}) != 936:
        raise ValueError('Registered schedule identity collision/count mismatch')
    return jobs


def ledger():
    path = OUT/'job_ledger.json'
    expected = schedule()
    if path.exists():
        rows = read(path)
        if [r['definition'] for r in rows] != expected:
            raise ValueError('Saved schedule changed')
    else:
        rows = [dict(definition=r, status='NOT_STARTED') for r in expected]
        write(path, rows)
    return rows


def update(rows, job_id, status, **details):
    row = next(r for r in rows if r['definition']['job_id'] == job_id)
    row.update(status=status, **details)
    write(OUT/'job_ledger.json', rows)


def freeze(path, calibration, artifacts, inputs):
    if calibration['smoke_only'] or calibration['test_ids_used']:
        raise ValueError('Smoke/test provenance cannot freeze')
    model_hash = calibration['identity']['model_sha256']
    files = {str(Path(p).relative_to(ROOT)): sha(p) for p in artifacts}
    if model_hash not in files.values():
        raise ValueError('Model identity is not bound to files')
    if calibration['identity']['model_id'] == 'gru':
        proofs = [read(p) for p in artifacts if str(p).endswith('.json')]
        selected = [r for r in proofs if r.get('status') == 'TRAIN_VALIDATION_SELECTED' and r.get('parameters_sha256') == model_hash]
        if len(selected) != 1:
            raise ValueError('Selected real benchmark training proof required')
        trial = selected[0]['training']['selected']
        if trial['smoke_only'] or trial['training_ids'] != calibration['training_ids'] or trial['validation_ids'] != calibration['validation_ids']:
            raise ValueError('Training/calibration identity mismatch')
    payload = dict(calibration=calibration, artifacts_sha256=files, input_identity=inputs,
         phase11_sources_sha256=sources(), phase10_lock_sha256=sha(ROOT/'connectome/Results/phase10/results/definition_lock.json'),
         phase10_artifact_index_sha256=sha(ROOT/'connectome/Results/phase10/results/delivery_artifact_index.json'),
         manifest_sha256=sha(ROOT/'connectome/phase5_5/results/benchmark_manifest.json'), test_inference_authorized=False)
    payload['payload_sha256'] = digest(payload)
    write(path, payload, immutable=True)
    verify_freeze(path)
    return payload


def verify_freeze(path):
    saved = read(path)
    payload = saved.pop('payload_sha256')
    if digest(saved) != payload or saved['phase11_sources_sha256'] != sources():
        raise ValueError('Freeze payload/source mismatch')
    if saved['calibration']['smoke_only'] or saved['calibration']['test_ids_used']:
        raise ValueError('Invalid freeze provenance')
    if saved['manifest_sha256'] != sha(ROOT/'connectome/phase5_5/results/benchmark_manifest.json'):
        raise ValueError('Manifest changed')
    for key, path_suffix in (('phase10_lock_sha256', 'definition_lock.json'), ('phase10_artifact_index_sha256', 'delivery_artifact_index.json')):
        if saved[key] != sha(ROOT/'connectome/Results/phase10/results'/path_suffix):
            raise ValueError('Phase 10 identity changed')
    for name, value in saved['artifacts_sha256'].items():
        if sha(ROOT/name) != value:
            raise ValueError('Frozen artifact changed')
    return saved


def completed_trial(directory, training, validation, seed, rate, inputs, *, smoke=False):
    """Read a completed trial without training or registering it again."""
    from .training import restore
    report = read(directory/'report.json')
    current = read(directory/'current.json')
    contract = current['contract']
    ids = lambda rows: [{k:r[k] for k in ('scenario_id','group_id','split','cohort','label','role')} for r in rows]
    expected = dict(contract, seed=seed, rate=rate, config=config(), sources_sha256=sources(),
                    input_identity=inputs, training=ids(training), validation=ids(validation), smoke_only=smoke)
    net, _, state = restore(directory, expected)
    if (not state['finished'] or report['smoke_only'] != smoke or report['seed'] != seed or report['learning_rate'] != rate
            or report['history'] != state['history'] or report['best_epoch'] != state['best_epoch']
            or report['validation_bce'] != state['best_bce'] or report['updates'] != state['adam_updates']
            or report['parameters_sha256'] != sha(directory/'selected.npz')
            or report['training_ids'] != [r['scenario_id'] for r in training]
            or report['validation_ids'] != [r['scenario_id'] for r in validation]):
        raise ValueError('Completed trial proof differs from its checkpoint')
    with np.load(directory/'selected.npz', allow_pickle=False) as saved:
        if set(saved.files) != set(net.p) or any(not np.array_equal(saved[k], state['_best'][k]) for k in saved.files):
            raise ValueError('Completed selected parameters differ')
        selected = {k:saved[k].copy() for k in saved.files}
    return GRU(321,16,seed,selected), report


def selected_gru(mapping, seed, training, validation, inputs, jobs):
    from .manual_stop import boundary
    candidates = []
    for rate in config()['learning_rates']:
        job = next(r['definition'] for r in jobs if r['definition']['kind'] == 'gru_trial' and r['definition']['mapping'] == mapping
                   and r['definition']['seed'] == seed and r['definition']['rate'] == rate)
        directory = OUT/'training'/job['job_id']
        status = next(r['status'] for r in jobs if r['definition']['job_id'] == job['job_id'])
        if status == 'FAILED_NO_REPLACEMENT':
            raise ValueError('Recorded failed trial cannot be silently retried')
        boundary()
        if status == 'COMPLETE' or (directory/'report.json').exists():
            net, report = completed_trial(directory, training, validation, seed, rate, inputs)
        else:
            update(jobs, job['job_id'], 'RUNNING_OR_RESUMING')
            net, report = train_trial(training, validation, seed, rate, directory, inputs)
        candidates.append((net, report))
        if status != 'COMPLETE':
            update(jobs, job['job_id'], 'COMPLETE', report=str((directory/'report.json').relative_to(ROOT)),
                   parameters_sha256=report['parameters_sha256'])
        boundary()
    net, report = min(candidates, key=lambda pair: (pair[1]['validation_bce'], pair[1]['learning_rate']))
    folder = OUT/'selected'/str(mapping)
    path = folder/f'gru_{seed}.npz'
    arrays(path, **net.p)
    record = dict(status='TRAIN_VALIDATION_SELECTED', parameters_sha256=sha(path), seed=seed, mapping=mapping,
          training=dict(selected=report, candidates=[r for _, r in candidates], failed_trials=[]))
    write(path.with_suffix('.json'), record, immutable=True)
    return net, [path, path.with_suffix('.json')]


def calibrate_job(job, dataset, training, validation, inputs, net=None, model_artifacts=None, linear=None):
    from .manual_stop import boundary
    key = job['job_id']
    folder = OUT/'calibration'/key
    proof = folder/'freeze.json'
    if proof.exists():
        return verify_freeze(proof)
    model_id = job['model_id']
    if model_id == 'gru':
        model_hash = sha(model_artifacts[0])
    elif model_id in ('feature_only', 'linear_temporal'):
        model = linear if linear is not None else dict(rule='fixed scaled population channel mean', trainable_parameters=0)
        path = OUT/'minimal'/str(job['mapping'])/(model_id+'.json')
        write(path, model, immutable=True)
        model_artifacts = [path]
        model_hash = sha(path)
    else:
        weights, setting, bank = load_network(model_id, dataset.pipeline.circuit, job['condition'])
        model_artifacts = [ROOT/'connectome/Results/phase10/results'/bank['path']]
        model_hash = bank['weights_sha256']
    identity = freeze_identity(model_id, model_hash, job.get('condition', 'native'), job['mapping'])
    # Per-clip atomic scores allow interrupted calibration to reuse checked work.
    sets, diagnostics = [], []
    for records in (training, validation):
        scored = []
        for row in records:
            sid = row['scenario_id']
            path = folder/'scores'/f'{sid}.npz'
            meta_path = path.with_suffix('.json')
            contract = dict(identity=identity, input_sha256=dataset.index[sid]['sha256'], phase11_sources_sha256=sources())
            if meta_path.exists():
                meta = read(meta_path)
                if meta['contract'] != contract or sha(path) != meta['sha256']:
                    raise ValueError('Score cache identity mismatch')
                with np.load(path, allow_pickle=False) as f:
                    score = f['score'].copy()
                diagnostic = meta['diagnostics']
            else:
                drive = dataset.load(sid)
                if model_id not in ('gru', 'feature_only', 'linear_temporal'):
                    result = rate_trace(drive, dataset.pipeline, weights, setting)
                    score = result['score']
                    diagnostic = result['diagnostics']
                    arrays(path, score=score, dn_activity=result['dn_activity'], final_state=result['states'][-1])
                else:
                    score = score_model(model_id, drive, dataset.pipeline, gru=net, linear=linear)
                    diagnostic = dict(finite=bool(np.isfinite(score).all()), score_min=float(score.min()), score_max=float(score.max()))
                    arrays(path, score=score)
                write(meta_path, dict(contract=contract, sha256=sha(path), diagnostics=diagnostic))
            scored.append(dict(**{k: row[k] for k in ('scenario_id', 'group_id', 'split', 'cohort', 'label', 'role')},
                               identity=identity, score=score))
            diagnostics.append(dict(scenario_id=sid, **diagnostic))
            boundary()
        sets.append(scored)
    calibration = assess(*sets, identity)
    write(folder/'assessments.json', calibration, immutable=True)
    write(folder/'diagnostics.json', diagnostics, immutable=True)
    # Assert threshold serialization preserves even the smallest positive float.
    reloaded = read(folder/'assessments.json')
    if reloaded['threshold'] != calibration['threshold']:
        raise ValueError('Threshold serialization mismatch')
    # Primary identical reference/minimal calibrations must reproduce Phase 8.
    if job['mapping'] == 'uniform_population' and job.get('condition', 'native') == 'native' and model_id in ('circuit', 'feature_only', 'linear_temporal'):
        prior = read(ROOT/'connectome/phase8/completion/results/selections'/f'{model_id}.json')
        if prior['threshold'] != calibration['threshold']:
            raise ValueError('Identical primary condition differs from frozen Phase 8 threshold')
    input_files = [dataset.directory/'index.json']
    if dataset.fields is not None:
        input_files.append(dataset.directory/'mapping.json')
    return freeze(proof, calibration, model_artifacts+input_files+[folder/'assessments.json', folder/'diagnostics.json'], inputs)


def execute(primary):
    from .manual_stop import boundary
    from connectome.scripts.phase7.pipeline import FrozenPipeline
    rows = ledger()
    mappings = ['uniform_population'] if primary else config()['mapping_seeds']
    for mapping in mappings:
        boundary()
        dataset = Dataset(FrozenPipeline(), mapping)
        inputs = dataset.prepare()
        training, validation = dataset.records('train'), dataset.records('validation')
        boundary()
        validate_coverage(training, 'train')
        validate_coverage(validation, 'validation')
        linear_rows = [dict(**{k: r[k] for k in ('scenario_id', 'group_id', 'split', 'cohort', 'label', 'role')},
                            filtered_features=minimal_features(dataset.load(r['scenario_id']), dataset.pipeline)[1]) for r in training]
        linear = fit_linear(linear_rows)
        if mapping == 'uniform_population':
            prior = read(ROOT/'connectome/phase8/completion/results/linear_model.json')
            if linear != prior:
                raise ValueError('Primary linear fit differs from frozen Phase 8 coefficients/provenance')
        selected = {}
        for seed in config()['training_seeds']:
            try:
                selected[seed] = selected_gru(mapping, seed, training, validation, inputs, rows)
            except Exception as error:
                active = [r for r in rows if r['status'] == 'RUNNING_OR_RESUMING']
                for r in active:
                    update(rows, r['definition']['job_id'], 'FAILED_NO_REPLACEMENT', error=str(error), traceback=traceback.format_exc())
                raise
        for row in rows:
            job = row['definition']
            if job['mapping'] != mapping or job['kind'] != 'calibration':
                continue
            if row['status'] == 'FAILED_NO_REPLACEMENT':
                raise ValueError('Recorded failed calibration cannot be silently retried')
            boundary()
            if row['status'] == 'COMPLETE':
                verify_freeze(OUT/'calibration'/job['job_id']/'freeze.json')
                continue
            update(rows, job['job_id'], 'RUNNING_OR_RESUMING')
            try:
                net, artifacts = selected[job['seed']] if job['model_id'] == 'gru' else (None, None)
                calibrate_job(job, dataset, training, validation, inputs, net, artifacts,
                              linear=linear if job['model_id'] == 'linear_temporal' else None)
                update(rows, job['job_id'], 'COMPLETE', freeze=str((OUT/'calibration'/job['job_id']/'freeze.json').relative_to(ROOT)))
                boundary()
            except Exception as error:
                update(rows, job['job_id'], 'FAILED_NO_REPLACEMENT', error=str(error), traceback=traceback.format_exc())
                raise
        dataset.frame_arrays.cache_clear()
    return dict(status='PASS', mappings=mappings,
                completed_jobs=sum(r['status'] == 'COMPLETE' for r in rows), held_out_inference_runs=0)
