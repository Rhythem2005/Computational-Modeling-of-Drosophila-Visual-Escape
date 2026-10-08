"""Validation module for Phase 4 simulation.

Validates:
1. Loaded circuit against frozen CSV (exact integer match)
2. Matrix W[post,pre] convention on named edges
3. Weight transformations (raw, normalized, signed)
4. File immutability (SHA-256 hashes before/after)
5. Bitwise determinism across repeated runs
6. Numerical stability checks (NaN, Inf, divergence)
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np

from . import dynamics, inputs, loader, readouts, simulator


def validate_circuit_loading(circuit: loader.CircuitData) -> list[dict[str, Any]]:
    """Validate loaded circuit data against frozen contract.

    Returns list of {check, status, detail} dicts.
    """
    results = []

    def check(label: str, ok: bool, detail: str = ""):
        results.append({"check": label, "status": "PASS" if ok else "FAIL", "detail": detail})

    C = loader.CONTRACT

    check("n_neurons", circuit.n_neurons == C["n_neurons"],
          f"got {circuit.n_neurons}")
    check("n_edges", len(circuit.edges_df) == C["n_edges"],
          f"got {len(circuit.edges_df)}")
    check("total_synapses", int(circuit.edges_df["weight"].sum()) == C["total_synapses"],
          f"got {int(circuit.edges_df['weight'].sum())}")
    check("max_raw_weight", int(circuit.edges_df["weight"].max()) == C["max_raw_weight"],
          f"got {int(circuit.edges_df['weight'].max())}")
    check("matrix_shape", circuit.W_raw.shape == (321, 321),
          f"got {circuit.W_raw.shape}")
    check("nonzero_count", np.count_nonzero(circuit.W_raw) == C["n_edges"],
          f"got {np.count_nonzero(circuit.W_raw)}")
    check("no_self_loops",
          len(circuit.edges_df[circuit.edges_df["bodyId_pre"] == circuit.edges_df["bodyId_post"]]) == 0)
    check("unique_body_ids", circuit.nodes_df["bodyId"].is_unique)

    # Population counts
    for ntype, expected in C["population_counts"].items():
        actual = len(circuit.nodes_df[circuit.nodes_df["type"] == ntype])
        check(f"{ntype}_count", actual == expected, f"got {actual}")

    # DN body IDs
    for dn_type, sides in C["dn_body_ids"].items():
        for side, expected_bid in sides.items():
            actual_bid = circuit.get_dn_body_id(dn_type, side)
            check(f"{dn_type}_{side}_bodyId", actual_bid == expected_bid,
                  f"expected {expected_bid}, got {actual_bid}")

    # Named edge verification
    edge_checks = loader.verify_named_edges(circuit)
    for ec in edge_checks:
        check(f"edge_{ec['description']}", ec["status"] == "PASS",
              str(ec))

    return results


def validate_sign_convention(
    circuit: loader.CircuitData,
    sign_map: dict[str, float],
    W_signed: np.ndarray,
) -> list[dict[str, Any]]:
    """Validate sign convention applied correctly."""
    results = []

    def check(label: str, ok: bool, detail: str = ""):
        results.append({"check": label, "status": "PASS" if ok else "FAIL", "detail": detail})

    # Check that all neurotransmitters have signs
    unique_nts = set(circuit.nt_map.values())
    for nt in unique_nts:
        check(f"nt_{nt}_in_sign_map", nt in sign_map, f"NT: {nt}")

    # Verify sign is correctly applied: for each presynaptic neuron,
    # W_signed[:, col] == sign * W_norm[:, col]
    for bid in circuit.body_ids:
        nt = circuit.nt_map[bid]
        sign = sign_map[nt]
        col = circuit.id_to_idx[bid]
        expected = sign * circuit.W_norm[:, col]
        match = np.allclose(W_signed[:, col], expected, atol=1e-15)
        if not match:
            check(f"sign_bodyId_{bid}", False,
                  f"Sign mismatch for bodyId {bid} (nt={nt}, sign={sign})")
            break
    else:
        check("sign_all_neurons", True, "All signs correctly applied")

    # Verify raw -> norm -> signed chain is inspectable
    max_w = loader.CONTRACT["max_raw_weight"]
    # Check one specific edge
    pre_bid = 81112
    post_bid = 531898
    if pre_bid in circuit.id_to_idx and post_bid in circuit.id_to_idx:
        pre_idx = circuit.id_to_idx[pre_bid]
        post_idx = circuit.id_to_idx[post_bid]
        raw_val = circuit.W_raw[post_idx, pre_idx]
        norm_val = circuit.W_norm[post_idx, pre_idx]
        signed_val = W_signed[post_idx, pre_idx]
        nt = circuit.nt_map[pre_bid]
        sign = sign_map[nt]

        check("raw_to_norm", abs(norm_val - raw_val / max_w) < 1e-10,
              f"raw={raw_val}, norm={norm_val}, expected={raw_val / max_w}")
        check("norm_to_signed", abs(signed_val - sign * norm_val) < 1e-10,
              f"norm={norm_val}, signed={signed_val}, sign={sign}")

    return results


def validate_numerical_stability(
    W_signed: np.ndarray,
    tau: np.ndarray,
    gain: float,
    dt: float,
) -> list[dict[str, Any]]:
    """Validate numerical stability properties."""
    results = []

    def check(label: str, ok: bool, detail: str = ""):
        results.append({"check": label, "status": "PASS" if ok else "FAIL", "detail": detail})

    # Spectral radius
    spectral_radius = dynamics.compute_spectral_radius(W_signed, gain)
    max_real_ev = dynamics.compute_max_real_eigenvalue(W_signed, gain)

    check("spectral_radius_computed", True,
          f"spectral_radius = {spectral_radius:.6f}")
    check("max_real_eigenvalue_computed", True,
          f"max_real_eigenvalue = {max_real_ev:.6f}")

    # For Euler stability with tau, need dt/tau * max_real_ev < 1
    # (linearized stability near zero fixed point)
    min_tau = float(np.min(tau))
    effective_gain = dt / min_tau * max_real_ev
    check("euler_stability_criterion",
          effective_gain < 1.0,
          f"dt/min_tau * max_real_ev = {effective_gain:.6f} (must be < 1)")

    return results


def validate_determinism(
    circuit: loader.CircuitData,
    config: dict,
) -> list[dict[str, Any]]:
    """Validate bitwise determinism by running simulation twice."""
    results = []

    def check(label: str, ok: bool, detail: str = ""):
        results.append({"check": label, "status": "PASS" if ok else "FAIL", "detail": detail})

    # Short run with some input
    short_config = {**config, "duration": 50}
    u_func = inputs.make_population_input(circuit, {"LC4": 1.0})

    _, states1, _ = simulator.run_simulation(circuit, short_config, u_func)
    _, states2, _ = simulator.run_simulation(circuit, short_config, u_func)

    check("bitwise_determinism",
          np.array_equal(states1, states2),
          "Two identical runs produce identical states")

    # Check no NaN/Inf
    check("no_nan_run1", not np.any(np.isnan(states1)))
    check("no_inf_run1", not np.any(np.isinf(states1)))

    return results


def validate_file_immutability(
    pre_hashes: dict[str, str],
    phase3_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Verify Phase 3 files were not modified by comparing hashes."""
    if phase3_dir is None:
        phase3_dir = loader.PHASE3_DIR

    results = []

    def check(label: str, ok: bool, detail: str = ""):
        results.append({"check": label, "status": "PASS" if ok else "FAIL", "detail": detail})

    for fname, pre_hash in pre_hashes.items():
        fpath = phase3_dir / fname
        if not fpath.exists():
            check(f"immutability_{fname}", False, "File not found")
            continue
        post_hash = loader.compute_sha256(fpath)
        check(f"immutability_{fname}",
              pre_hash == post_hash,
              f"pre={pre_hash[:16]}... post={post_hash[:16]}...")

    return results


def validate_no_blowup(states: np.ndarray, label: str = "") -> list[dict[str, Any]]:
    """Check simulation states for NaN, Inf, and extreme values."""
    results = []
    prefix = f"{label}_" if label else ""

    def check(name: str, ok: bool, detail: str = ""):
        results.append({"check": f"{prefix}{name}", "status": "PASS" if ok else "FAIL", "detail": detail})

    check("no_nan", not np.any(np.isnan(states)),
          f"NaN count: {np.sum(np.isnan(states))}")
    check("no_inf", not np.any(np.isinf(states)),
          f"Inf count: {np.sum(np.isinf(states))}")

    max_val = float(np.max(np.abs(states)))
    check("no_extreme_values", max_val < 1e6,
          f"max |state| = {max_val:.4f}")

    return results

def validate_no_saturation(states: np.ndarray, clip_max: float | None, label: str = "") -> list[dict[str, Any]]:
    """Check that no neuron hits the clip_max and no trace is flat for >50ms."""
    results = []
    prefix = f"{label}_" if label else ""
    if clip_max is None:
        return results

    def check(name: str, ok: bool, detail: str = ""):
        results.append({"check": f"{prefix}{name}", "status": "PASS" if ok else "FAIL", "detail": detail})

    max_val = float(np.max(states))
    is_saturated = max_val >= clip_max * 0.999
    check("no_clip_saturation", not is_saturated, f"max_val={max_val:.4f}, clip_max={clip_max}")

    # A trace is flatly saturated if it stays exactly constant for >50ms at a value > 1e-3, 
    # and we specifically worry if it's at the clip_max or if it artificially flatlines.
    flat_saturation = False
    if len(states) >= 50:
        for i in range(len(states) - 50):
            # Check if any neuron is exactly identical for 50 steps at a value near clip_max
            window = states[i:i+50, :]
            # std over time for each neuron
            std_over_time = np.std(window, axis=0)
            mean_over_time = np.mean(window, axis=0)
            # Find neurons that are flat and high
            flat_and_high = (std_over_time < 1e-9) & (mean_over_time >= clip_max * 0.999)
            if np.any(flat_and_high):
                flat_saturation = True
                break
    
    check("no_flat_saturation", not flat_saturation, "Checked for 50ms flat traces at clip_max")
    return results
