"""Gate A: verify delivered bytes, actual graph invariants and partition guards."""
import platform
import sys
import numpy as np
import yaml
from .common import ROOT, OUT, read, sha, write


def verify():
    from connectome.scripts.phase10.common import config, sources
    from connectome.scripts.phase10.validate import job_plan
    from connectome.scripts.phase10.data import TrainingDataset, manifest_rows, validate_coverage
    from connectome.scripts.phase10.networks import load_network
    from connectome.scripts.phase9.evidence import verify_definition
    from connectome.scripts.phase7.pipeline import FrozenPipeline
    parent = verify_definition()
    base = ROOT/'connectome/Results/phase10/results'
    lock = read(base/'definition_lock.json')
    if lock['sources_sha256'] != sources() or lock['config'] != config():
        raise ValueError('Phase 10 source/config lock mismatch')
    index = read(base/'delivery_artifact_index.json')
    for name, value in index.items():
        if sha(ROOT/name) != value:
            raise ValueError(f'Phase 10 delivered artifact mismatch: {name}')
    if read(base/'validation_results.json')['status'] != 'PASS':
        raise ValueError('Phase 10 validation did not pass')
    pipeline = FrozenPipeline()
    bank = read(base/'network_bank.json')
    plan = read(base/'benchmark_job_plan.json')
    if job_plan(bank) != plan:
        raise ValueError('Job plan differs from frozen definition')
    for row in bank:
        for condition in ('native', 'stability_matched'):
            load_network(row['model_id'], pipeline.circuit, condition)
    rows = manifest_rows()
    groups = {}
    for row in rows:
        previous = groups.setdefault(row['group_id'], row['cohort'])
        if previous != row['cohort']:
            raise ValueError('Family crosses cohort boundary')
    class NoAccess:
        def load_frozen_encoded(self, _):
            raise AssertionError('Forbidden input opened before guard')
    guard = TrainingDataset(NoAccess())
    blocked = 0
    for row in rows:
        if row['split'] == 'test':
            try:
                guard.load(row['scenario_id'])
            except ValueError:
                blocked += 1
            else:
                raise AssertionError('Test access accepted')
    counts = {}
    for split in ('train', 'validation'):
        selected = [r for r in rows if r['cohort'] == split]
        validate_coverage(selected, split)
        counts[split] = dict(clips=len(selected), families=len({r['group_id'] for r in selected}))
    report = dict(status='PASS', phase10_source_hashes=len(lock['sources_sha256']),
                  phase10_delivered_hashes=len(index), graph_architectures=len(bank), graph_conditions=2*len(bank),
                  partitions=counts, rejected_test_identities_before_file_access=blocked,
                  parent_protocol=parent['protocol_id'], parent_definition_sha256=sha(ROOT/'connectome/phase9/results/definition_lock.json'),
                  manifest_sha256=sha(ROOT/'connectome/phase5_5/results/benchmark_manifest.json'),
                  config=config(), schedule=dict(gru_trials=2*len(plan['gru_training']),
                  selected_grus=len(plan['gru_training']), calibrations=len(plan['rate_models'])+len(plan['minimal_controls'])+len(plan['gru_training'])),
                  environment=dict(python=sys.version, numpy=np.__version__, yaml=yaml.__version__, platform=platform.platform()),
                  held_out_inference_runs=0)
    write(OUT/'gate_A.json', report)
    return report
