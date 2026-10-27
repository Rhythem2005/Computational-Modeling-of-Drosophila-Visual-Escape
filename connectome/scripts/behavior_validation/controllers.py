"""Score-before-update controllers; observations contain no evaluator geometry."""
import numpy as np
from connectome.scripts.phase4 import dynamics, simulator
from connectome.scripts.phase10.gru import sigmoid
from connectome.scripts.phase10.models import minimal_features

class Controller:
    def __init__(self, model, pipeline, net=None):
        if model not in ('circuit', 'feature_only', 'no_action', 'gru'):
            raise ValueError('Unsupported controller')
        self.model = model
        self.pipeline = pipeline
        self.net = net
        self.assigned = np.array(pipeline.encoder.mapping['channel_index'])
        ids = {int(b):k for k,b in enumerate(pipeline.circuit.body_ids)}
        self.primary = [ids[10010], ids[10001]]
        self.sim = pipeline.simulation_config
        self.tau = simulator.build_tau_vector(pipeline.circuit, self.sim)
        self.bias = simulator.build_bias_vector(pipeline.circuit, self.sim)
        if (self.sim['dt'] != 1 or self.sim['gain'] != .5 or self.sim['input_scale'] != .4
                or self.sim['noise_std'] != 0 or np.any(self.bias)):
            raise ValueError('Frozen dynamics mismatch')
        if model == 'gru' and (net is None or net.input_dim != 321 or net.hidden != 16):
            raise ValueError('Registered trained GRU required')
        self.reset()

    def reset(self):
        self.state = np.zeros((1,16), dtype=np.float64) if self.model == 'gru' else np.zeros(321, dtype=np.float64)
        self.clipped = 0
        self.updates = 0
        self.cached_drive = None
        self.projections = None
        self.feature_score = None
        # Preserve the frozen batch GEMM/GEMV dimensions without exposing any
        # future observation or advancing a future hidden state. Rows of the
        # input projection are independent: repeating the CURRENT vector is
        # arithmetic padding, never a predicted frame or recurrent rollout.
        self.readout_states = np.zeros((1,1001,16),dtype=np.float64) if self.model=='gru' else None

    def prepare(self, drive):
        key = drive.tobytes()
        if self.cached_drive == key:
            return
        if self.model == 'gru':
            x = .4*np.broadcast_to(drive,(1,1000,321)).copy()
            p = self.net.p
            self.projections = {g:x@p['W'+g]+p['b'+g] for g in 'rzn'}
        elif self.model == 'feature_only':
            # Advanced-index column means in minimal_features reduce in a
            # different order from a contiguous one-row mean. Use the actual
            # frozen function and dimensions instead of relaxing equality.
            padded = np.broadcast_to(drive,(1000,321)).copy()
            self.feature_score = minimal_features(padded,self.pipeline)[0]
        self.cached_drive = key

    def validate_drive(self, drive):
        if (drive.dtype != np.float64 or drive.shape != (321,) or not np.isfinite(drive).all()
                or np.any(drive < 0) or np.any(drive > 1) or np.any(drive[self.assigned < 0])):
            raise ValueError('Invalid ordered visual drive or direct DN input')

    def score(self, drive):
        self.validate_drive(drive)
        if self.model == 'gru':
            self.readout_states[:,self.updates] = self.state
            return float(sigmoid(self.readout_states[:,:1000]@self.net.p['w'] + self.net.p['b'][0])[0,self.updates])
        if self.model == 'circuit':
            return float(self.state[self.primary].mean())
        if self.model == 'feature_only':
            self.prepare(drive)
            return float(self.feature_score[self.updates])
        return 0.0

    def advance(self, drive):
        self.validate_drive(drive)
        if self.model == 'circuit':
            scaled = self.sim['input_scale']*drive
            preclip = self.sim['gain']*(self.pipeline.weights@self.state)+self.bias+scaled
            self.clipped += int(np.count_nonzero(preclip > self.sim['clip_max']))
            self.state = dynamics.euler_step(self.state, self.pipeline.weights, self.bias, scaled,
                    self.tau, self.sim['gain'], self.sim['dt'], self.sim['clip_max'])
        elif self.model == 'gru':
            p = self.net.p
            self.prepare(drive)
            projections = {g:self.projections[g][:,self.updates] for g in 'rzn'}
            prev = self.state
            r = sigmoid(projections['r']+prev@p['Ur'])
            z = sigmoid(projections['z']+prev@p['Uz'])
            n = np.tanh(projections['n']+(r*prev)@p['Un'])
            self.state = (1-z)*prev+z*n
        self.updates += 1
        if not np.isfinite(self.state).all():
            raise FloatingPointError('Nonfinite controller state')

    def state_vector(self):
        if self.model in ('feature_only', 'no_action'):
            return np.empty(0, dtype=np.float64)
        return self.state.ravel().copy()
