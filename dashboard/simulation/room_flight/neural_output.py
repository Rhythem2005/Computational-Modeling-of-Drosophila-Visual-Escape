"""Read actual DN states and modeled synaptic inputs; never infer a motor policy.

This adapter consumes the verified FrozenCircuit, not GRU hidden units. Values
are arbitrary rate-model units. A contribution is gain*W[post,pre]*x[pre],
not measured synaptic current, functional connectivity, or causal attribution.
"""
import numpy as np


class MissingMotorMapping(RuntimeError):
    pass


class AnatomicalOutput:
    def __init__(self, circuit):
        self.circuit = circuit
        data = circuit.pipeline.circuit
        self.ids = np.asarray(data.body_ids, dtype=np.int64)
        if len(set(self.ids.tolist())) != len(self.ids):
            raise ValueError('Duplicate anatomical IDs')
        self.indices = np.asarray(data.get_dn_indices(), dtype=int)
        self.dn_ids = self.ids[self.indices].copy()
        self.weights = np.asarray(circuit.pipeline.weights, dtype=np.float64).copy()
        self.gain = float(circuit.pipeline.simulation_config['gain'])
        if (self.weights.shape != (len(self.ids), len(self.ids))
                or not np.isfinite(self.weights).all() or not np.isfinite(self.gain)):
            raise ValueError('Invalid anatomical weight matrix or gain')
        if not np.array_equal(self.ids, circuit.ids):
            raise ValueError('Anatomical state ID order mismatch')

    def sample(self, state):
        state = np.asarray(state)
        if state.shape != self.ids.shape or not np.isfinite(state).all() or np.any(state < 0):
            raise ValueError('Expected finite nonnegative anatomical state in frozen ID order')
        contributions = self.gain * self.weights[self.indices] * state[None, :]
        return dict(dn_body_ids=self.dn_ids.copy(), dn_activity=state[self.indices].copy(),
                    dn_recurrent_input=contributions.sum(axis=1),
                    motor_mapping_available=False)

    def incoming(self, body_id, state):
        """All structural inputs, preserving IDs and zero-activity connections."""
        self.sample(state)  # validate before inspecting
        matches = np.flatnonzero(self.ids == body_id)
        if len(matches) != 1:
            raise ValueError('Unknown anatomical body ID')
        row = self.weights[matches[0]]
        pres = np.flatnonzero(row)
        return dict(pre_body_ids=self.ids[pres].copy(), weights=row[pres].copy(),
                    modeled_contributions=self.gain * row[pres] * np.asarray(state)[pres])

    def motor_command(self):
        raise MissingMotorMapping(
            'No evidence-backed DN-to-3D motor mapping is implemented. '
            'Front room RGB is outside the frozen encoder domain; receptive fields '
            'and downstream motor circuitry are missing. No planner fallback is allowed.')
