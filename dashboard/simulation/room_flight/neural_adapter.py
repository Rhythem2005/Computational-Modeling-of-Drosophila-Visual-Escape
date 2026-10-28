"""Optional frozen FRONT-view diagnostic. It never grants surround motor permission."""
import numpy as np

class NullDiagnostic:
    ids=np.empty(0,dtype=np.int64)
    threshold=None
    role='unavailable'
    def observe(self,observation):pass
    def sample(self,k):return dict(score=None,sustained_score=None,state=np.empty(0),drive=np.empty(0),channels=np.empty(0),valid=None)
    def advance(self):pass
    def frame_record(self,observations):return np.empty((len(observations),0)),np.empty((len(observations),0))
    def state_vector(self):return np.empty(0)
    def verify_preserved(self):return True

class FrontCircuitDiagnostic:
    role='diagnostic_front_view_only_not_surround_controller'
    def __init__(self,snapshot_record,duration_ms):
        from ..avoidance.circuit import FrozenCircuit
        self.circuit=FrozenCircuit(snapshot_record,duration_ms);self.ids=self.circuit.ids;self.threshold=self.circuit.freeze['threshold']
        from .neural_output import AnatomicalOutput
        self.output=AnatomicalOutput(self.circuit)
    def observe(self,observation):
        index=next((i for i,v in enumerate(observation.views) if v.id=='front'),None)
        if index is None:raise ValueError('Front-view diagnostic requires an explicitly calibrated front view')
        image=observation.images[index]
        if image.shape!=(256,256,3):raise ValueError('Frozen diagnostic requires 256x256 front RGB; no silent resizing')
        # New diagnostic preprocessing, explicitly uncalibrated in this room domain.
        gray=np.rint(image.astype(float)@np.array([.2126,.7152,.0722])).astype(np.uint8)
        self.circuit.observe(gray,observation.time_ms)
    def frame_record(self,observations):
        frames=[]
        for o in observations:
            index=next(i for i,v in enumerate(o.views) if v.id=='front')
            frames.append(np.rint(o.images[index].astype(float)@np.array([.2126,.7152,.0722])).astype(np.uint8))
        encoded=self.circuit.pipeline.encoder.encode(np.stack(frames),np.array([o.time_ms/1000 for o in observations]))
        return encoded.channels,encoded.drive
    def sample(self,k):
        state=self.circuit.sample(k);encoded=self.circuit.encoded
        state.update(channels=encoded.channels[-1].copy(),valid=False)
        state.update(self.output.sample(state['state']))
        return state
    def advance(self):self.circuit.advance()
    def state_vector(self):return self.circuit.controller.state_vector()
    def verify_preserved(self):return self.circuit.verify_preserved()
