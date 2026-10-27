"""Run the existing encoder/circuit APIs only from their verified execution snapshot."""
import json, sys
from pathlib import Path
import numpy as np
from .contracts import digest

class FrozenCircuit:
    def __init__(self,snapshot_record,duration_ms):
        record=json.loads(Path(snapshot_record).read_text());root=Path(record['path']).resolve()
        for name,h in record['files_sha256'].items():
            if digest(root/name)!=h:raise ValueError('Historical snapshot changed: '+name)
        # Never turn an already imported active scientific namespace into a historical one.
        if any(k=='connectome' or k.startswith('connectome.') for k in sys.modules):raise RuntimeError('Launch a fresh process for the historical namespace')
        sys.path.insert(0,str(root))
        from connectome.scripts.phase7.pipeline import FrozenPipeline
        from connectome.scripts.behavior_validation.controllers import Controller
        from connectome.scripts.collision_threat_v1.protocol import legacy_rows
        from connectome.scripts.phase8.decoder import StreamingDecoder,Threshold
        self.pipeline=FrozenPipeline();self.controller=Controller('circuit',self.pipeline)
        self.freeze=legacy_rows(self.pipeline)['circuit'];self.stream=StreamingDecoder(Threshold(**self.freeze['threshold']),duration_ms)
        self.ids=np.asarray(self.pipeline.circuit.body_ids,dtype=np.int64)
        self.frames=[];self.times=[];self.encoded=None;self.drive=np.zeros(321,dtype=np.float64);self.record=record
    def observe(self,image,time_ms):
        self.frames.append(image.copy());self.times.append(time_ms/1000)
        self.encoded=self.pipeline.encoder.encode(np.stack(self.frames),np.asarray(self.times,dtype=np.float64))
        self.drive=self.encoded.drive[-1].copy()
    def sample(self,k):
        score=self.controller.score(self.drive);result=self.stream.update(float(k),score)
        return dict(score=score,state=self.controller.state_vector(),drive=self.drive.copy(),**result)
    def advance(self):self.controller.advance(self.drive)
    def verify_preserved(self):
        root=Path(self.record['path'])
        return all(digest(root/n)==h for n,h in self.record['files_sha256'].items())
