"""One threshold budget per model/condition/mapping; no test selection."""
import json
import numpy as np
from .common import ROOT, OUT, config, digest, sha, sources, write_json
from .data import validate_coverage, array_digest
from connectome.scripts.phase8.decoder import decode_score, Threshold
from connectome.scripts.phase8.candidates import build_candidates, rank_validation_assessments


def calibrate(training,validation,identity,*,smoke=False):
    if not smoke:
        validate_coverage(training,'train');validate_coverage(validation,'validation')
    for records,split in ((training,'train'),(validation,'validation')):
        if not records or any(r['split']!=split or r['cohort']!=split for r in records):raise ValueError('Calibration partition violation')
        if len({r['scenario_id'] for r in records})!=len(records) or {r['label'] for r in records}!={0,1}:raise ValueError('Duplicate/missing binary class')
        if any(r['identity']!=identity for r in records):raise ValueError('Model/weights/mapping differ across calibration records')
    if {r['group_id'] for r in training}&{r['group_id'] for r in validation}:raise ValueError('Family leakage')
    times=np.arange(1000,dtype=np.float64);neg=[]
    for r in training:
        decoded=decode_score(times,r['score'],1000.,Threshold('always_silent',None))
        if r['label']==0:neg.append(dict(**{k:r[k] for k in ('scenario_id','group_id','split','cohort','label','role')},
                                        sustained_score_max=float(decoded.sustained_score[decoded.eligible].max())))
    plan=build_candidates(neg);assessments=[]
    for candidate in plan['candidates']:
        timely=false=early=0;pos=sum(r['label']==1 for r in validation);negative=len(validation)-pos
        for r in validation:
            first=decode_score(times,r['score'],1000.,Threshold(**candidate['threshold'])).first_event_ms
            timely+=r['label']==1 and first is not None and 200<=first<1000
            false+=r['label']==0 and first is not None;early+=first is not None and first<200
        assessments.append(dict(candidate_id=candidate['candidate_id'],threshold=candidate['threshold'],timely_tpr=timely/pos,
                                full_episode_fpr=false/negative,pre_onset_decisions=early))
    selected=rank_validation_assessments(assessments)
    return dict(identity=identity,threshold=selected['threshold'],candidate_plan=plan,assessments=assessments,selected=selected,
                training_ids=[r['scenario_id'] for r in training],validation_ids=[r['scenario_id'] for r in validation],
                score_hashes={r['scenario_id']:array_digest(r['score']) for r in training+validation},
                test_ids_used=[],smoke_only=smoke,status='SYNTHETIC_SMOKE_ONLY' if smoke else 'CALIBRATED_TRAIN_VALIDATION_ONLY')


def save_freeze(name,calibration,model_files):
    from connectome.scripts.phase5.config import validate_id
    validate_id(name)
    if calibration['smoke_only']:raise ValueError('A synthetic smoke calibration cannot authorize test inference')
    if not model_files:raise ValueError('Model artifacts must be bound')
    model_id=calibration['identity']['model_id']
    if model_id not in ('gru','feature_only','linear_temporal'):
        bank=json.loads((OUT/'network_bank.json').read_text())
        candidates=[r for r in bank if r['model_id']==model_id and r['weights_sha256']==calibration['identity']['model_sha256']]
        if len(candidates)!=1 or not candidates[0]['eligible_for_use'] or not candidates[0]['conditions'][calibration['identity']['gain_condition']]['stable']:
            raise ValueError('Unknown or ineligible network/model hash')
    artifacts={}
    for name_in in model_files:
        path=(ROOT/name_in).resolve()
        if not path.is_relative_to(OUT.resolve()):raise ValueError('Model artifact outside Phase 10')
        artifacts[str(path.relative_to(ROOT))]=sha(path)
    if calibration['identity']['model_sha256'] not in artifacts.values():raise ValueError('Identity not bound to supplied model files')
    if calibration['identity']['model_id']=='gru':
        records=[json.loads((ROOT/p).read_text()) for p in artifacts if p.endswith('.json')]
        selected=[r for r in records if r.get('status')=='TRAIN_VALIDATION_SELECTED' and r.get('parameters_sha256')==calibration['identity']['model_sha256']]
        if len(selected)!=1:raise ValueError('GRU has no selected benchmark training proof; untrained/smoke weights cannot freeze')
        trial=selected[0]['training']['selected']
        if trial['smoke_only'] or set(trial['training_ids'])!=set(calibration['training_ids']) or set(trial['validation_ids'])!=set(calibration['validation_ids']):
            raise ValueError('GRU training/calibration provenance differs')
    record=dict(version='1.0.0',calibration=calibration,sources_sha256=sources(),config_sha256=digest(config()),
                model_artifacts_sha256=artifacts,manifest_sha256=sha(ROOT/'connectome/phase5_5/results/benchmark_manifest.json'))
    from connectome.scripts.phase9.evidence import verify_definition
    record['parent_evidence']=verify_definition()
    record['payload_sha256']=digest(record);write_json(OUT/'freezes'/f'{name}.json',record,immutable=True)
    return record


def load_freeze(name):
    from connectome.scripts.phase5.config import validate_id
    validate_id(name);record=json.loads((OUT/'freezes'/f'{name}.json').read_text());payload=record.pop('payload_sha256')
    if digest(record)!=payload or record['sources_sha256']!=sources() or record['config_sha256']!=digest(config()):raise ValueError('Freeze/config/source mismatch')
    if record['calibration']['smoke_only'] or record['calibration']['test_ids_used']:raise ValueError('Invalid freeze provenance')
    if sha(ROOT/'connectome/phase5_5/results/benchmark_manifest.json')!=record['manifest_sha256']:raise ValueError('Manifest changed')
    from connectome.scripts.phase9.evidence import verify_definition
    if verify_definition()!=record['parent_evidence']:raise ValueError('Frozen parent pipeline changed')
    for p,value in record['model_artifacts_sha256'].items():
        if sha(ROOT/p)!=value:raise ValueError('Model weights changed after calibration')
    return record
