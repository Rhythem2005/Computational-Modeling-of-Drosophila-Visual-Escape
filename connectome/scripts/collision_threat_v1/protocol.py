"""Exact reviewed candidate, no default calibration or training dispatch."""
import numpy as np
from connectome.scripts.phase11.jobs import verify_freeze
from connectome.scripts.phase10.networks import load_network
from .common import ROOT,BASE,read,sha

def authorization():
    approved=read(BASE/'candidate_authorization.json')
    proposed=read(BASE/'candidate_manifest.json')
    if (approved.get('status')!='USER_APPROVED_EXACT_RULE_MANIFEST'
            or approved['specification_sha256']!=sha(BASE/'decision_rule_spec.md')
            or approved['candidate_manifest_sha256']!=sha(BASE/'candidate_manifest.json')
            or approved['stage_a_audit_sha256']!=sha(BASE/'1793092658671112000/information_audit.json')
            or approved['attempt_cap']!=60 or approved['candidate_count']!=1
            or approved['threshold_searches']!=0 or not approved['point_observer_limitation_acknowledged']
            or proposed['candidate_id']!='image_constant_velocity_point_observer_v1'):
        raise ValueError('Missing or changed exact-rule authorization')
    return approved

def legacy_rows(pipeline):
    rows={}
    base=ROOT/'connectome/Results/phase11/results/calibration'
    ledger={r['definition']['job_id']:r for r in read(ROOT/'connectome/Results/phase11/results/job_ledger.json')}
    for model,suffix in (('circuit','_native'),('feature_only','')):
        name=f'cal_uniform_population_{model}{suffix}';path=base/name/'freeze.json'
        if ledger[name]['status']!='COMPLETE':raise ValueError('Required control calibration incomplete')
        f=verify_freeze(path);identity=f['calibration']['identity']
        if (identity['model_id']!=model or identity['mapping']!='uniform_population'
                or identity['gain_condition']!='native' or f['test_inference_authorized']):
            raise ValueError('Legacy control identity mismatch')
        if model=='circuit':
            weights,setting,_=load_network(model,pipeline.circuit,'native')
            if not setting['stable'] or not np.array_equal(weights,pipeline.weights):
                raise ValueError('Frozen circuit weights differ')
        rows[model]=dict(threshold=f['calibration']['threshold'],freeze_sha256=sha(path))
    rows['no_action']=dict(threshold=dict(kind='always_silent',value=None),freeze_sha256=None)
    return rows
