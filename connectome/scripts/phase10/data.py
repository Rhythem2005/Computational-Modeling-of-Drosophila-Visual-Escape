"""Train/validation-only data access with immutable identities and provenance."""
from dataclasses import dataclass
import json
import numpy as np
from .common import ROOT, sha, digest
from connectome.scripts.phase6.encoder import causal_hold


def manifest_rows():
    return json.loads((ROOT/'connectome/phase5_5/results/benchmark_manifest.json').read_text())['scenarios']


def validate_coverage(records, split):
    expected={r['scenario_id']:r for r in manifest_rows() if r['cohort']==split and r['split']==split}
    if split not in ('train','validation') or len(records)!=len(expected) or {r['scenario_id'] for r in records}!=set(expected):
        raise ValueError('Incomplete/forbidden benchmark partition')
    for r in records:
        if any(r.get(k)!=expected[r['scenario_id']][k] for k in ('group_id','split','cohort','label','role')):
            raise ValueError('Identity or label differs from frozen manifest')


class TrainingDataset:
    """The Phase 10 loader has no test-access switch, even for smoke tests."""
    def __init__(self, pipeline):
        self.pipeline=pipeline;self.rows={r['scenario_id']:r for r in manifest_rows()};self.audit=[]

    def load(self, scenario_id):
        row=self.rows.get(scenario_id)
        if row is None or row['split'] not in ('train','validation') or row['cohort']!=row['split']:
            raise ValueError('Held-out/test data is forbidden in Phase 10')
        # Permission precedes file loading. The encoder never sees metadata.
        encoded=self.pipeline.load_frozen_encoded(scenario_id)
        inputs=step_drive(encoded,self.pipeline)
        self.audit.append(dict(scenario_id=scenario_id,cohort=row['cohort'],input_sha256=array_digest(inputs)))
        return dict(**{k:row[k] for k in ('scenario_id','group_id','split','cohort','label','role')},inputs=inputs)

    def records(self,split):
        if split not in ('train','validation'):raise ValueError('Forbidden partition')
        # Lazy batch loading limits full-benchmark training memory.
        out=[]
        for row in self.rows.values():
            if row['cohort']==split:
                sid=row['scenario_id']
                out.append(dict(**{k:row[k] for k in ('scenario_id','group_id','split','cohort','label','role')},
                                inputs=lambda sid=sid:self.load(sid)['inputs']))
        validate_coverage(out,split)
        return out


def array_digest(a):
    return digest(dict(shape=list(a.shape),dtype=str(a.dtype),bytes_sha256=__import__('hashlib').sha256(a.tobytes()).hexdigest()))


def validate_drive(drive,pipeline):
    if not isinstance(drive,np.ndarray) or drive.dtype!=np.float64 or drive.shape!=(1000,321) or not np.isfinite(drive).all() or np.any(drive<0) or np.any(drive>1):
        raise ValueError('Expected finite unscaled float64 (1000,321) drive in [0,1]')
    dn=np.asarray(pipeline.encoder.mapping['channel_index'])<0
    if np.any(drive[:,dn]):raise ValueError('Descending neurons cannot receive direct visual input')
    return drive


def step_drive(encoded,pipeline):
    from connectome.scripts.phase7.pipeline import MillisecondInput
    adapter=MillisecondInput(encoded,pipeline.circuit,pipeline.encoder)
    if encoded.timestamps_s[-1]>=1:raise ValueError('Frame beyond half-open episode')
    return validate_drive(adapter.sample(np.arange(1000,dtype=np.float64)),pipeline)


def hold_spatial_drive(drive,timestamps_s,body_ids,pipeline):
    if not np.array_equal(body_ids,np.asarray(pipeline.circuit.body_ids,dtype=np.int64)) or np.asarray(body_ids).dtype!=np.int64:
        raise ValueError('Spatial body-ID order differs')
    if timestamps_s[-1]>=1:raise ValueError('Frame beyond episode')
    return validate_drive(causal_hold(drive,timestamps_s,np.arange(1000,dtype=np.float64)/1000),pipeline)
