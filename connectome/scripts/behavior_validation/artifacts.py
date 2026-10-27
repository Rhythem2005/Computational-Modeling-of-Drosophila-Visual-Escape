"""Read-only inclusion checks. Never dispatch training or calibration jobs."""
import numpy as np
from connectome.scripts.phase10.gru import GRU
from connectome.scripts.phase10.networks import load_network
from connectome.scripts.phase11.jobs import verify_freeze, completed_trial
from .common import ROOT, read, sha, digest

PRODUCTION = ROOT/'connectome/Results/phase11/results'

def load_roster(pipeline):
    planning = read(ROOT/'connectome/Results/behavior_validation_planning_20261027/saved_state_verification.json')
    ledger = {r['definition']['job_id']: r for r in read(PRODUCTION/'job_ledger.json')}
    roster = {}
    for mapping in ('uniform_population', '55010'):
        group = []
        for model, suffix in (('circuit', '_native'), ('feature_only', '')):
            path = PRODUCTION/'calibration'/f'cal_{mapping}_{model}{suffix}'/'freeze.json'
            if ledger[path.parent.name]['status'] != 'COMPLETE':
                raise ValueError('Uncompleted fixed-control calibration')
            freeze = verify_freeze(path)
            identity = freeze['calibration']['identity']
            if (str(identity['mapping']) != mapping or identity['model_id'] != model
                    or identity['gain_condition'] != 'native' or freeze['test_inference_authorized']):
                raise ValueError('Control identity mismatch')
            if model == 'circuit':
                weights, condition, _ = load_network('circuit', pipeline.circuit, 'native')
                if not condition['stable'] or not np.array_equal(weights, pipeline.weights):
                    raise ValueError('Native weights differ from frozen anatomical circuit')
            group.append(dict(id=model, model=model, threshold=freeze['calibration']['threshold'],
                              freeze_sha256=sha(path), net=None))
        group.append(dict(id='no_action', model='no_action', threshold={'kind':'always_silent','value':None},
                          freeze_sha256=None, net=None))
        selected = [s for s in planning['selected'] if str(s['mapping']) == mapping]
        if sorted(s['seed'] for s in selected) != list(range(55100,55110)):
            raise ValueError('Incomplete planned ten-seed roster')
        for s in sorted(selected, key=lambda x:x['seed']):
            path = ROOT/s['freeze']
            if sha(path) != s['freeze_sha256'] or ledger[path.parent.name]['status'] != 'COMPLETE':
                raise ValueError('Calibration changed since saved cutoff')
            freeze = verify_freeze(path)
            candidates = []
            for rate in (.0003,.001):
                key = f"train_{s['mapping']}_{s['seed']}_{str(rate).replace('.', 'p')}"
                if ledger[key]['status'] != 'COMPLETE':
                    raise ValueError('Partial or failed training trial')
                folder = PRODUCTION/'training'/key
                contract = read(folder/'current.json')['contract']
                _, report = completed_trial(folder, contract['training'], contract['validation'],
                    s['seed'], rate, contract['input_identity'])
                best = min(report['history'], key=lambda x:x['validation_bce'])
                if best['epoch'] != report['best_epoch']:
                    raise ValueError('Not earliest best epoch')
                candidates.append(report)
            chosen = min(candidates, key=lambda x:(x['validation_bce'],x['learning_rate']))
            model_path = PRODUCTION/'selected'/mapping/f"gru_{s['seed']}.npz"
            record = read(model_path.with_suffix('.json'))
            if (record['status'] != 'TRAIN_VALIDATION_SELECTED' or record['seed'] != s['seed']
                    or str(record['mapping']) != mapping or record['training']['candidates'] != candidates
                    or record['training']['selected'] != chosen or record['training']['failed_trials']
                    or sha(model_path) != chosen['parameters_sha256']
                    or record['parameters_sha256'] != s['parameters_sha256']
                    or chosen['parameters_sha256'] != s['parameters_sha256']):
                raise ValueError('Selected GRU proof mismatch')
            identity = freeze['calibration']['identity']
            if (identity['model_id'] != 'gru' or str(identity['mapping']) != mapping
                    or identity['model_sha256'] != s['parameters_sha256']
                    or freeze['calibration']['threshold'] != s['threshold']):
                raise ValueError('Selected GRU calibration identity mismatch')
            with np.load(model_path, allow_pickle=False) as f:
                net = GRU(321,16,s['seed'],{k:f[k].copy() for k in f.files})
            if net.parameter_count != 16241:
                raise ValueError('Unexpected parameter count')
            group.append(dict(id=f"gru_{s['seed']}", model='gru', seed=s['seed'], net=net,
                              parameters_sha256=s['parameters_sha256'], threshold=s['threshold'],
                              freeze_sha256=sha(path)))
        roster[mapping] = group
    return roster

def public_roster(roster):
    return {mapping:[{k:v for k,v in row.items() if k!='net'} for row in rows] for mapping,rows in roster.items()}
