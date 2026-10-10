"""Unit tests for Phase 4 modules.

Run with: ./venv/bin/python -m pytest connectome/scripts/phase4/tests/test_phase4.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from connectome.scripts.phase4 import dynamics, inputs, loader, readouts, simulator, validation


@pytest.fixture(scope="module")
def circuit():
    return loader.load_circuit()


@pytest.fixture(scope="module")
def sign_map():
    return {"acetylcholine": 1.0, "GABA": -1.0, "glutamate": -1.0}


# ============================================================
# Loader tests
# ============================================================


class TestLoader:
    """Test circuit loading and validation."""

    def test_neuron_count(self, circuit):
        assert circuit.n_neurons == 321

    def test_edge_count(self, circuit):
        assert len(circuit.edges_df) == 11557

    def test_total_synapses(self, circuit):
        assert int(circuit.edges_df["weight"].sum()) == 91023

    def test_max_weight(self, circuit):
        assert int(circuit.edges_df["weight"].max()) == 172

    def test_min_weight(self, circuit):
        assert int(circuit.edges_df["weight"].min()) >= 3

    def test_matrix_shape(self, circuit):
        assert circuit.W_raw.shape == (321, 321)
        assert circuit.W_norm.shape == (321, 321)

    def test_nonzero_entries(self, circuit):
        assert np.count_nonzero(circuit.W_raw) == 11557

    def test_no_self_loops(self, circuit):
        for i in range(circuit.n_neurons):
            assert circuit.W_raw[i, i] == 0.0

    def test_unique_body_ids(self, circuit):
        assert len(set(circuit.body_ids)) == 321

    def test_population_counts(self, circuit):
        for ntype, expected in loader.CONTRACT["population_counts"].items():
            actual = len(circuit.get_population_indices(ntype))
            assert actual == expected, f"{ntype}: expected {expected}, got {actual}"

    def test_hemisphere_counts(self, circuit):
        for ntype, sides in loader.CONTRACT["hemisphere_counts"].items():
            for side, expected in sides.items():
                actual = len(circuit.get_population_indices(ntype, side=side))
                assert actual == expected, f"{ntype} {side}: expected {expected}"

    def test_dn_body_ids(self, circuit):
        for dn_type, sides in loader.CONTRACT["dn_body_ids"].items():
            for side, expected_bid in sides.items():
                actual_bid = circuit.get_dn_body_id(dn_type, side)
                assert actual_bid == expected_bid

    def test_w_post_pre_convention(self, circuit):
        """Verify W[post, pre] convention: the max weight edge is
        pre=81112 (LC4) -> post=531898 (DNp04), weight=172."""
        pre_idx = circuit.id_to_idx[81112]
        post_idx = circuit.id_to_idx[531898]
        assert circuit.W_raw[post_idx, pre_idx] == 172
        assert circuit.W_raw[pre_idx, post_idx] != 172  # NOT reversed

    def test_normalization(self, circuit):
        """W_norm = W_raw / 172."""
        max_w = 172
        mask = circuit.W_raw > 0
        expected_norm = circuit.W_raw[mask] / max_w
        actual_norm = circuit.W_norm[mask]
        assert np.allclose(actual_norm, expected_norm, atol=1e-10)

    def test_named_edges(self, circuit):
        results = loader.verify_named_edges(circuit)
        for r in results:
            assert r["status"] == "PASS", f"Named edge check failed: {r}"

    def test_neurotransmitter_present(self, circuit):
        """All neurons must have predicted_nt."""
        for bid in circuit.body_ids:
            assert bid in circuit.nt_map
            assert circuit.nt_map[bid] is not None

    def test_sign_map_coverage(self, circuit):
        """All neurotransmitters in circuit must be in default sign map."""
        sign_map = {"acetylcholine": 1.0, "GABA": -1.0, "glutamate": -1.0}
        for bid in circuit.body_ids:
            nt = circuit.nt_map[bid]
            assert nt in sign_map, f"NT '{nt}' for bodyId {bid} not in sign_map"


class TestSignedWeights:
    """Test signed weight matrix construction."""

    def test_signed_shape(self, circuit, sign_map):
        W_signed = loader.build_signed_weight_matrix(circuit, sign_map)
        assert W_signed.shape == (321, 321)

    def test_all_ach_positive(self, circuit, sign_map):
        """All neurons are ACh -> all signs should be +1 -> W_signed == W_norm."""
        W_signed = loader.build_signed_weight_matrix(circuit, sign_map)
        assert np.allclose(W_signed, circuit.W_norm, atol=1e-15)


    def test_negative_sign_hypothetical(self, circuit):
        """If we set ACh to -1, all weights should be negated."""
        sign_map_neg = {"acetylcholine": -1.0, "GABA": -1.0, "glutamate": -1.0}
        W_signed = loader.build_signed_weight_matrix(circuit, sign_map_neg)
        assert np.allclose(W_signed, -circuit.W_norm, atol=1e-15)

    def test_sign_path_synthetic(self, circuit):
        """Test sign convention on a synthetic circuit with multiple NTs."""
        import copy
        syn_circuit = copy.deepcopy(circuit)
        # Assign 4 neurons with different NTs
        syn_circuit.nt_map[circuit.body_ids[0]] = "acetylcholine"
        syn_circuit.nt_map[circuit.body_ids[1]] = "GABA"
        syn_circuit.nt_map[circuit.body_ids[2]] = "glutamate"
        syn_circuit.nt_map[circuit.body_ids[3]] = "unknown_nt"

        # Test unknown NT raises error
        sign_map = {"acetylcholine": 1.0, "GABA": -1.0, "glutamate": -1.0}
        with pytest.raises(ValueError, match="not in sign_map"):
            loader.build_signed_weight_matrix(syn_circuit, sign_map)

        # Test signs are applied correctly
        syn_circuit.nt_map[circuit.body_ids[3]] = "acetylcholine"  # Fix the unknown NT
        # Fake weights
        syn_circuit.W_norm = np.zeros_like(syn_circuit.W_norm)
        syn_circuit.W_norm[5, 0] = 1.0 # ACh
        syn_circuit.W_norm[5, 1] = 1.0 # GABA
        syn_circuit.W_norm[5, 2] = 1.0 # Glu

        W_signed = loader.build_signed_weight_matrix(syn_circuit, sign_map)
        assert W_signed[5, 0] == 1.0
        assert W_signed[5, 1] == -1.0
        assert W_signed[5, 2] == -1.0



# ============================================================
# Dynamics tests
# ============================================================


class TestDynamics:
    """Test dynamics core functions."""

    def test_phi_relu_positive(self):
        z = np.array([1.0, 2.0, 3.0])
        assert np.array_equal(dynamics.phi_relu(z), z)

    def test_phi_relu_negative(self):
        z = np.array([-1.0, -2.0, 0.0])
        expected = np.array([0.0, 0.0, 0.0])
        assert np.array_equal(dynamics.phi_relu(z), expected)

    def test_phi_relu_mixed(self):
        z = np.array([-1.0, 0.5, 2.0])
        expected = np.array([0.0, 0.5, 2.0])
        assert np.array_equal(dynamics.phi_relu(z), expected)

    def test_phi_relu_clip(self):
        z = np.array([0.5, 5.0, 100.0])
        result = dynamics.phi_relu(z, clip_max=10.0)
        expected = np.array([0.5, 5.0, 10.0])
        assert np.array_equal(result, expected)

    def test_euler_step_decay(self):
        """With zero input and no connections, state should decay."""
        n = 3
        x = np.ones(n)
        W = np.zeros((n, n))
        b = np.zeros(n)
        u = np.zeros(n)
        tau = np.full(n, 10.0)
        x_new = dynamics.euler_step(x, W, b, u, tau, gain=1.0, dt=1.0)
        # x_new = x + (1/10) * (-x + max(0, 0)) = x - x/10 = 0.9 * x
        expected = 0.9 * x
        assert np.allclose(x_new, expected)

    def test_simulate_deterministic(self):
        """Two identical runs must give identical results."""
        n = 3
        W = np.array([[0, 0.1, 0], [0, 0, 0.1], [0.1, 0, 0]], dtype=np.float64)
        tau = np.full(n, 10.0)
        u_func = lambda t, n: np.array([1.0, 0.0, 0.0])

        t1, s1 = dynamics.simulate(W, tau, 0.5, 1.0, 100.0, u_func)
        t2, s2 = dynamics.simulate(W, tau, 0.5, 1.0, 100.0, u_func)
        assert np.array_equal(s1, s2)

    def test_spectral_radius(self):
        W = np.array([[0, 1], [0, 0]], dtype=np.float64)
        sr = dynamics.compute_spectral_radius(W, 1.0)
        assert abs(sr) < 1e-10  # nilpotent matrix has spectral radius 0

    def test_spectral_radius_identity(self):
        W = np.eye(3)
        sr = dynamics.compute_spectral_radius(W, 2.0)
        assert abs(sr - 2.0) < 1e-10

    @pytest.mark.parametrize(
        "kwargs,match",
        [
            ({"dt": 0.0}, "dt and duration"),
            ({"duration": 10.5}, "integer multiple"),
            ({"tau": np.array([10.0, 0.0])}, "time constants"),
        ],
    )
    def test_simulate_rejects_invalid_numerics(self, kwargs, match):
        params = {
            "W_signed": np.zeros((2, 2)),
            "tau": np.full(2, 10.0),
            "gain": 0.5,
            "dt": 1.0,
            "duration": 10.0,
            "u_func": lambda t, n: np.zeros(n),
        }
        params.update(kwargs)
        with pytest.raises(ValueError, match=match):
            dynamics.simulate(**params)

    def test_simulate_rejects_bad_input_shape(self):
        with pytest.raises(ValueError, match="input function returned shape"):
            dynamics.simulate(
                np.zeros((2, 2)), np.full(2, 10.0), 0.5, 1.0, 10.0,
                lambda t, n: np.zeros(n + 1),
            )


# ============================================================
# Inputs tests
# ============================================================


class TestInputs:
    """Test input generation functions."""

    def test_zero_input(self, circuit):
        u_func = inputs.make_zero_input()
        u = u_func(0.0, circuit.n_neurons)
        assert np.all(u == 0.0)
        assert len(u) == circuit.n_neurons

    def test_population_input_lc4(self, circuit):
        u_func = inputs.make_population_input(circuit, {"LC4": 1.0})
        u = u_func(0.0, circuit.n_neurons)
        lc4_indices = circuit.get_population_indices("LC4")
        assert all(u[i] == 1.0 for i in lc4_indices)
        # Non-LC4 should be zero
        non_lc4 = [i for i in range(circuit.n_neurons) if i not in lc4_indices]
        assert all(u[i] == 0.0 for i in non_lc4)

    def test_population_input_side(self, circuit):
        u_func = inputs.make_population_input(circuit, {"LC4": 1.0}, side="left")
        u = u_func(0.0, circuit.n_neurons)
        lc4_left = circuit.get_population_indices("LC4", side="left")
        lc4_right = circuit.get_population_indices("LC4", side="right")
        assert all(u[i] == 1.0 for i in lc4_left)
        assert all(u[i] == 0.0 for i in lc4_right)

    def test_pulse_input_timing(self, circuit):
        u_func = inputs.make_pulse_input(circuit, {"LC4": 1.0}, onset=10.0, offset=20.0)
        u_before = u_func(5.0, circuit.n_neurons)
        u_during = u_func(15.0, circuit.n_neurons)
        u_after = u_func(25.0, circuit.n_neurons)
        assert np.all(u_before == 0.0)
        assert np.max(u_during) == 1.0
        assert np.all(u_after == 0.0)

    def test_invalid_population_rejected(self, circuit):
        with pytest.raises(ValueError, match="not LC4/LPLC2"):
            inputs.make_population_input(circuit, {"DNp01": 1.0})

    def test_invalid_bodyid_rejected(self, circuit):
        # DNp01 left bodyId
        with pytest.raises(ValueError, match="not LC4/LPLC2"):
            inputs.make_static_input(circuit, {10010: 1.0})

    def test_invalid_side_rejected(self, circuit):
        with pytest.raises(ValueError, match="side must be"):
            inputs.make_population_input(circuit, {"LC4": 1.0}, side="centre")

    def test_invalid_pulse_window_rejected(self, circuit):
        with pytest.raises(ValueError, match="onset/offset"):
            inputs.make_pulse_input(circuit, {"LC4": 1.0}, onset=20.0, offset=10.0)

    def test_time_varying_input_rejects_nonvisual_bodyid(self, circuit):
        u_func = inputs.make_time_varying_input(circuit, lambda t: {10010: 1.0})
        with pytest.raises(ValueError, match="restricted to visual"):
            u_func(0.0, circuit.n_neurons)


# ============================================================
# Readouts tests
# ============================================================


class TestReadouts:
    """Test readout extraction."""

    def test_extract_readouts(self, circuit):
        n = circuit.n_neurons
        times = np.arange(0, 11, dtype=np.float64)
        states = np.random.default_rng(42).random((11, n))
        ro = readouts.extract_readouts(circuit, times, states, dt=1.0)

        # Check all DNs present
        for dn in readouts.DN_TYPES:
            assert dn in ro.dn_readouts
            for side in ["left", "right"]:
                assert side in ro.dn_readouts[dn]
                nr = ro.dn_readouts[dn][side]
                assert len(nr.time_series) == 11

        # Check L-R differences computed
        assert len(ro.lr_differences) == 5


    def test_t90_nan_logic(self):
        # Silent neuron: max < 0.01 * global_max
        times = np.array([0.0, 1.0, 2.0])
        ts_silent = np.array([0.0, 0.05, 0.05])
        nr = readouts.NeuronReadout(body_id=1, neuron_type="DNp01", side="left", time_series=ts_silent)
        nr.compute_stats(times, 1.0, global_max=10.0)
        assert np.isnan(nr.t90)

        # Pulse: ss < 0.95 * max
        ts_pulse = np.array([0.0, 10.0, 0.1])
        nr = readouts.NeuronReadout(body_id=1, neuron_type="DNp01", side="left", time_series=ts_pulse)
        nr.compute_stats(times, 1.0, global_max=10.0)
        assert np.isnan(nr.t90)

        # Steady: ss >= 0.95 * max
        ts_steady = np.array([0.0, 8.0, 10.0])
        nr = readouts.NeuronReadout(body_id=1, neuron_type="DNp01", side="left", time_series=ts_steady)
        nr.compute_stats(times, 1.0, global_max=10.0)
        assert not np.isnan(nr.t90)
        assert nr.t90 == 2.0

    def test_pulse_reports_peak_but_not_t90(self):
        times = np.array([0.0, 1.0, 2.0])
        trace = np.array([0.0, 10.0, 0.1])
        nr = readouts.NeuronReadout(1, "DNp01", "left", trace)
        nr.compute_stats(times, 1.0, global_max=10.0)
        assert nr.peak_time == 1.0
        assert nr.steady_state == 0.1
        assert np.isnan(nr.t90)

    def test_readout_summary(self, circuit):
        n = circuit.n_neurons
        times = np.arange(0, 11, dtype=np.float64)
        states = np.zeros((11, n))
        ro = readouts.extract_readouts(circuit, times, states, dt=1.0)
        summary = readouts.readout_summary_dict(ro)
        assert "dn_neurons" in summary
        assert "lr_differences" in summary
        for dn in summary["dn_neurons"].values():
            for neuron in dn.values():
                assert neuron["t90_ms"] is None


class TestConfiguration:
    def test_repository_config_is_valid(self):
        config = simulator.load_config()
        simulator.validate_config(config)

    def test_unknown_tau_population_rejected(self, circuit):
        config = simulator.load_config()
        config["tau"] = {**config["tau"], "not_a_population": 10.0}
        with pytest.raises(ValueError, match="unknown population"):
            simulator.build_tau_vector(circuit, config)

    def test_unsupported_activation_rejected(self):
        config = simulator.load_config()
        config["phi"] = "sigmoid"
        with pytest.raises(ValueError, match="Only the documented"):
            simulator.validate_config(config)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
