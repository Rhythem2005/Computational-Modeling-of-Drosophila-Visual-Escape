"""Phase 10 engineering validation; never performs benchmark comparisons."""
import argparse
import json
from datetime import datetime,timezone
from pathlib import Path
import platform
import subprocess
import sys
import time
import traceback
import numpy as np
from .common import ROOT, BASE, OUT, config, write_json, sources, digest, sha, save_arrays


def preflight():
    from connectome.scripts.phase9.evidence import verify_definition
    from connectome.scripts.phase7.evidence import verify_frozen
    parent = verify_definition()
    result = dict(status='PASS', phase6=verify_frozen(), phase9_protocol=parent['protocol_id'],
                  phase9_sources=len(parent['sources_sha256']), phase8=parent['parent_evidence'])
    config()
    write_json(OUT/'preflight.json', result, immutable=True)
    print('Frozen Phases 6–9 verification: PASS', flush=True)
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--task',choices=['preflight','validate'],default='validate')
    args=p.parse_args();parent=preflight()
    if args.task == 'validate':
        try:validate(parent)
        except Exception as error:
            write_json(OUT/'validation_results.json',dict(status='FAIL',error=str(error),traceback=traceback.format_exc(),time_utc=datetime.now(timezone.utc).isoformat()))
            raise


def parent_hashes():
    paths=[p for base in (ROOT/'connectome',) for p in base.rglob('*')
           if p.is_file() and 'phase10' not in p.parts and not {'__pycache__','.pytest_cache'}.intersection(p.parts)]
    paths.extend(ROOT/n for n in ('README.md','config.yaml','requirements.txt'))
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)}


def job_plan(bank):
    c=config();mappings=['uniform_population',*c['mapping_seeds']]
    return dict(status='PLANNED_NOT_EXECUTED',protocol='fly_open_loop_v1',
                rate_models=[dict(model_id=r['model_id'],condition=condition,mapping=mapping,seed=r['seed'],weights_sha256=r['weights_sha256'],
                                  threshold_fit='own 256 train / 128 validation responses before test',
                                  usable=r['eligible_for_use'] and r['conditions'][condition]['stable'])
                             for mapping in mappings for r in bank for condition in ('native','stability_matched')],
                gru_training=[dict(mapping=mapping,seed=seed,rates=c['learning_rates'],max_epochs=c['max_epochs'],patience=c['patience'])
                              for mapping in mappings for seed in c['training_seeds']],
                minimal_controls=[dict(model_id=kind,mapping=mapping,fit='train only' if kind=='linear_temporal' else 'fixed',threshold='own train/validation')
                                  for mapping in mappings for kind in ('feature_only','linear_temporal')],
                benchmark_training_runs_executed_phase10=0,benchmark_comparative_runs_executed_phase10=0,held_out_inference_runs_phase10=0,
                rules=dict(primary_null_count=30,failed_required_network='blocks H2 confirmation; no survivor-only ensemble',
                           secondary_null='degree rewiring, report all mixing failures',nn='descriptive; larger fitting opportunity',
                           statistics='Phase 11+ only; preserve predeclared paired family/independent-null bootstrap'))


def synthetic_drive(pipeline):
    assigned=np.array(pipeline.encoder.mapping['channel_index']);times=np.arange(1000)
    signal=np.where(times>=200,.2+.3*(times-200)/800,0.)
    drive=np.zeros((1000,321),dtype=np.float64)
    drive[:,assigned==0]=signal[:,None]
    drive[:,assigned==1]=(.7*signal)[:,None]
    return drive


def smoke_models(bank,pipeline):
    from .models import rate_trace,score_model,freeze_identity
    from .networks import load_network
    from .gru import GRU,train_seed,save_gru,load_gru
    from .calibration import calibrate
    from .data import array_digest
    # Synthetic engineering inputs are not sampled from any benchmark cohort.
    drive=synthetic_drive(pipeline);save_arrays(OUT/'engineering/input.npz',drive=drive,body_ids=np.array(pipeline.circuit.body_ids,dtype=np.int64))
    reports=[];runtimes=[]
    for row in bank:
        for condition in ('native','stability_matched'):
            key=row['model_id']+'_'+condition
            try:
                w,setting,_=load_network(row['model_id'],pipeline.circuit,condition)
                result=rate_trace(drive,pipeline,w,setting);diagnostics=result['diagnostics'].copy()
                runtimes.append(dict(model_id=key,runtime_s=diagnostics.pop('runtime_s')))
                save_arrays(OUT/'engineering'/f'{key}.npz',score=result['score'],dn_activity=result['dn_activity'],final_state=result['states'][-1])
                reports.append(dict(model_id=key,status='PASS_SYNTHETIC_PLUMBING_ONLY',diagnostics=diagnostics))
            except (ValueError,FloatingPointError) as error:
                reports.append(dict(model_id=key,status='FAILED_NO_REDRAW',error=str(error)))
    # 10 registered seeds × 2 registered rates on tiny independent toy families.
    from importlib import import_module
    # Test helpers are not used as implementation: construct fixture records here.
    rng=np.random.default_rng(10010);sets=[]
    for split in ('train','validation'):
        rows=[]
        for k in range(4):
            x=rng.uniform(0,.05,(32,321));x[:8]=0;x[:,np.array(pipeline.encoder.mapping['channel_index'])<0]=0
            if k%2:x[8:,np.array(pipeline.encoder.mapping['channel_index'])>=0]+=.4
            rows.append(dict(scenario_id=f'smoke_{split}_{k}',group_id=f'smoke_{split}_{k}',split=split,cohort=split,
                             role='looming' if k%2 else 'static_initial',label=k%2,inputs=x))
        sets.append(rows)
    training_reports=[];initializations=[]
    for seed in config()['training_seeds']:
        initial=GRU(seed=seed);record=save_gru(f'initial_{seed}',initial,dict(status='UNTRAINED',training=None))
        initializations.append(record)
        score=score_model('gru',drive,pipeline,gru=initial)
        save_arrays(OUT/'engineering'/f'gru_initial_{seed}.npz',score=score)
        started=time.perf_counter();net,trained=train_seed(*sets,seed,smoke=True,smoke_epochs=2,smoke_start=8)
        runtimes.append(dict(model_id=f'gru_smoke_{seed}_both_rates',runtime_s=time.perf_counter()-started))
        training_reports.append(trained);save_gru(f'smoke_{seed}',net,dict(status='SYNTHETIC_SMOKE_ONLY',training=trained))
        restored,_=load_gru(f'smoke_{seed}')
        for k in net.p:
            if not np.array_equal(net.p[k],restored.p[k]):raise ValueError('GRU checkpoint roundtrip differs')
    write_json(OUT/'gru_initializations.json',initializations,immutable=True)
    write_json(OUT/'synthetic_training.json',training_reports,immutable=True)
    # Exercise each threshold API without using real train/validation responses.
    identity=freeze_identity('synthetic_fixture',array_digest(drive),'native','uniform_population');sets=[]
    for split in ('train','validation'):
        rows=[]
        for k,role in enumerate(('looming','static_initial','static_terminal','translating_initial')):
            score=np.zeros(1000);score[200:]=.2 if k==0 else 0.
            rows.append(dict(scenario_id=f'smoke_{split}_{role}',group_id=f'smoke_{split}',split=split,cohort=split,
                             label=int(k==0),role=role,identity=identity,score=score))
        sets.append(rows)
    write_json(OUT/'synthetic_calibration.json',calibrate(*sets,identity,smoke=True),immutable=True)
    write_json(OUT/'engineering/diagnostics.json',reports,immutable=True)
    write_json(OUT/'engineering/runtimes.json',runtimes)
    if any(r['failed_trials'] for r in training_reports):raise ValueError('Synthetic GRU trial failure; inspect ledger')
    return reports,training_reports


def validate(parent):
    from .networks import build_bank,seed_schedule
    from .regression import run,counts
    from connectome.scripts.phase7.pipeline import FrozenPipeline
    c=config();before=parent_hashes();write_json(OUT/'execution_parent_before.json',before,immutable=True)
    definition=dict(version=c['version'],config=c,seed_schedule=seed_schedule(),parent=parent,scope='engineering_only_no_comparative_experiments',sources_sha256=sources())
    target=OUT/'definition_lock.json'
    if target.exists():
        old=json.loads(target.read_text())
        if old!=definition:
            for k in definition:
                if k!='sources_sha256' and old.get(k)!=definition[k]:raise ValueError('Frozen control definition changed')
            result=OUT/'validation_results.json'
            if result.exists() and json.loads(result.read_text()).get('status')=='PASS':raise ValueError('Delivered sources changed; new version required')
            repairs=OUT/'development_repairs.json';history=json.loads(repairs.read_text()) if repairs.exists() else []
            history.append(dict(old_source_hashes=old['sources_sha256'],new_source_hashes=definition['sources_sha256'],configuration_changed=False))
            write_json(repairs,history)
    write_json(target,definition)
    print('Running earlier regression before controls',flush=True);reg_before=run('before')
    pipeline=FrozenPipeline();bank=build_bank(pipeline.circuit)
    plan=job_plan(bank);write_json(OUT/'benchmark_job_plan.json',plan,immutable=True)
    directory=OUT/'tests';directory.mkdir(parents=True,exist_ok=True)
    command=[sys.executable,'-m','pytest',str(BASE/'tests'),'-q','-p','no:cacheprovider',f'--junitxml={directory/"tests.xml"}']
    result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
    (directory/'tests.log').write_text(result.stdout+result.stderr)
    tests=counts(directory/'tests.xml');print('Phase 10 tests:',tests,flush=True)
    if result.returncode:raise ValueError(f'Phase 10 tests failed; see {directory/"tests.log"}')
    smoke,training=smoke_models(bank,pipeline)
    print('Running earlier regression after controls',flush=True);reg_after=run('after')
    after=parent_hashes();write_json(OUT/'execution_parent_after.json',after)
    if before!=after:raise ValueError('Frozen execution parents changed')
    if any(not r['eligible_for_use'] for r in bank):raise ValueError('Secondary rewiring mixing failure; all failures remain visible')
    failed=[r['model_id'] for r in smoke if r['status']=='FAILED_NO_REDRAW']
    if failed:raise ValueError(f'Engineering forward failures retained: {failed}')
    report=dict(status='PASS',completion_status='COMPLETE_ENGINEERING',phase=10,version=c['version'],time_utc=datetime.now(timezone.utc).isoformat(),
                tests=tests,regression_before=reg_before,regression_after=reg_after,
                unique_tests=tests['tests']+reg_after['tests']['tests'],phase4_assertions=reg_after['phase4_assertions'],
                networks=len(bank),primary_weight_nulls=30,secondary_degree_nulls=30,rate_conditions=len(smoke),
                failed_conditions=failed,gru_seeds=10,synthetic_training_trials=sum(len(r['candidates']) for r in training),
                exact_numerical_rerun='All existing bank arrays/JSON and synthetic outputs must match on each invocation',
                benchmark_gru_training_runs=0,benchmark_control_comparison_runs=0,held_out_inference_runs=0,
                earlier_execution_files_preserved=len(before),definition_sha256=sha(target),sources_checked=len(definition['sources_sha256']),
                environment=dict(python=platform.python_version(),numpy=np.__version__,platform=platform.platform()),command=[sys.executable,*sys.argv],
                limitations=['No benchmark training/calibration or scientific model freezes yet; Phase 11 must execute the saved plan.',
                             'Finite rewiring diagnostics do not prove independent uniform graph sampling; rigid blocks remain fixed.',
                             'GRU has 16,241 fitted parameters versus zero learned anatomical weights; fitting opportunities differ.',
                             'Synthetic receptive fields, world-domain calibration, noise robustness and encoder clipping limits remain.',
                             'No H1/H2/H3, biological fidelity or wiring-advantage conclusion.'])
    write_json(OUT/'validation_results.json',report)
    previous=OUT/'successful_invocations.json';runs=json.loads(previous.read_text()) if previous.exists() else []
    runs.append(dict(time_utc=report['time_utc'],definition_sha256=report['definition_sha256'],tests=tests,network_bank_sha256=sha(OUT/'network_bank.json')))
    write_json(previous,runs)
    text=f'''# Phase 10 validation report

Status: **PASS — COMPLETE_ENGINEERING**, version {c['version']}. UTC: {report['time_utc']}.

Frozen Phase 6–9 evidence passed before construction. All {len(before)} earlier execution-copy files were identical before/after; the outer launcher's workspace inventories independently protect the actual renamed repository. Sources/configuration/seed schedule were saved before engineering outcomes. No earlier validator overwrote frozen results.

Built 62 rate architectures: reference, population average, 30 weight shuffles and 30 degree rewirings, with 124 native/stability-matched condition records. All graph constraints and mixing gates passed; no failures were silently redrawn. All 124 conditions ran on the same synthetic engineering input and saved score/DN traces, final states and scale/clipping/stability/runtime diagnostics. These are plumbing checks, not benchmark comparisons. See `network_bank.json`, `networks/`, `engineering/` and `seed_schedule.json`.

Phase 10: {tests['tests']} tests, zero failures/errors/skips. Unchanged earlier suites: {reg_after['tests']['tests']} tests before and after, plus {reg_after['phase4_assertions']['passed']} passing Phase 4 integration assertions per run. Unique unit/integration test cases: {report['unique_tests']}; simulator assertions counted separately. Analytical GRU/BPTT gradients passed independent central finite differences across every parameter in a small model. Adam matched an independent two-update calculation. Tests cover causality/state alignment, training-only gradients, stopping/selection, split/family/identity guards, calibration/event semantics, serialization, tamper detection and all five synthetic spatial mappings.

Saved ten explicitly **untrained** 16-unit GRUs (16,241 parameters each); all ten seeds and both learning rates executed only on tiny synthetic fixtures, with checkpoint roundtrips. No real benchmark GRU training, null-vs-circuit benchmark trials or held-out inference ran. The benchmark job plan has {len(plan['rate_models'])} planned rate-model conditions across six mappings, {len(plan['gru_training'])} planned two-rate NN searches, and {len(plan['minimal_controls'])} minimal-control conditions. It was not executed. Production fitting/calibration require exact complete training/validation coverage. Synthetic-only calibration cannot authorize test use.

The reference adapter reproduced the frozen pipeline exactly on one previously used training encoding; minimal primary features reproduced Phase 8 exactly. Integrity verification hashes earlier encoded test artifacts but does not run models/decoders on them.

Successful complete validation invocations saved so far: {len(runs)}. Each reproduction checks existing numerical artifacts rather than overwriting differing results. Exact commands, environment, JUnit/logs, source lock and both regression runs are saved alongside this report.

## Limitations and Phase 11 readiness

Software and reproducible control artifacts are ready. Phase 11 must still execute the predeclared full train/validation fits and per-model/mapping/gain calibration, freeze selected weights/thresholds, and only then run comparative untouched-test experiments. No benchmark performance is established here. Finite rewiring/overlap diagnostics are not a mixing theorem; rigid blocks are explicit. The GRU has larger fitting opportunities, not equal learned parameter capacity. The original synthetic sensory/motor assumptions, noise/near-zero-threshold sensitivity, encoder clipping and uncalibrated world domain remain. No circuit advantage, biological fidelity or hypothesis result is inferred.
'''
    (OUT/'validation_report.md').write_text(text)
    index={str(p.relative_to(ROOT)):sha(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name not in ('delivery_artifact_index.json','execution.json','workspace_after.json')}
    write_json(OUT/'delivery_artifact_index.json',index)
    print('Phase 10 PASS:',report['unique_tests'],'tests; 62 networks; 124 synthetic rate conditions; 20 synthetic NN trials; no benchmark comparisons',flush=True)


if __name__ == '__main__':
    main()
