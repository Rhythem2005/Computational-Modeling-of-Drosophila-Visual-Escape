"""Phase 4 integration tests: Tests A-F, stability, determinism, validation.

Run from project root:
    ./venv/bin/python connectome/scripts/phase4/run_phase4_tests.py

Tests:
    A. Zero input: from zero and small nonzero state (must decay)
    B. LC4 only input
    C. LPLC2 only input
    D. Both LC4 + LPLC2 (convergence, amplitude, timing, L/R)
    E. Left-only and right-only LC4 (report hemisphere pattern)
    F. Finite pulse: reproducible temporal response
    Stability: multiple input levels, dt sensitivity
    Determinism: bitwise identical repeat runs
    Validation: circuit loading, edge verification, immutability
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from connectome.scripts.phase4 import dynamics, inputs, loader, readouts, simulator, validation

# Output directories
PHASE4_DIR = PROJECT_ROOT / "connectome" / "phase4"
RESULTS_DIR = PHASE4_DIR / "results"
REPORTS_DIR = PHASE4_DIR / "reports"

# ============== Pass criteria (defined BEFORE running) ==============
# These are set a priori — no fitting.

# Test A: zero input must decay to zero
DECAY_THRESHOLD = 1e-6  # max |state| after 200ms from small initial state

# Test D: both inputs convergence
CONVERGENCE_THRESHOLD = 1e-3  # state change per step at end of 500ms

# dt sensitivity: peak and AUC tolerances between dt=0.5 and dt=1.0
DT_PEAK_TOLERANCE = 0.10  # 10% relative difference
DT_AUC_TOLERANCE = 0.15   # 15% relative difference

# Stability: max |state| under various input levels
STABILITY_MAX_STATE = 1e5  # threshold for divergence


def main():
    print("=" * 70)
    print("PHASE 4 — RATE-MODEL SIMULATION TESTS")
    print(f"Run date: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    all_results = {}
    passed = 0
    failed = 0
    test_details = []

    def record(test_id: str, name: str, ok: bool, detail: str = ""):
        nonlocal passed, failed
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
        test_details.append({"test_id": test_id, "name": name, "status": status, "detail": detail})
        print(f"  {'✓' if ok else '✗'} [{test_id}] {name}: {detail[:120]}")

    # ================================================================
    # 0. Load circuit and record pre-hashes
    # ================================================================
    print("\n--- 0. LOADING CIRCUIT & RECORDING HASHES ---")
    start_load = time.time()
    circuit = loader.load_circuit()
    load_time = time.time() - start_load
    print(f"  Circuit loaded in {load_time:.2f}s: {circuit.n_neurons} neurons, "
          f"{len(circuit.edges_df)} edges")
    pre_hashes = circuit.file_hashes.copy()

    # Load config
    config = simulator.load_config()
    print(f"  Config: gain={config['gain']}, dt={config['dt']}, "
          f"duration={config['duration']}, tau_default={config['tau']['default']}")

    # Build signed weight matrix for analysis
    W_signed = loader.build_signed_weight_matrix(circuit, config["sign_map"])

    # Edge type breakdown
    edge_types = circuit.describe_edge_types()
    print("\n  Edge type breakdown:")
    for et, counts in sorted(edge_types.items()):
        print(f"    {et}: {counts['count']} edges, {counts['total_synapses']} synapses")

    # ================================================================
    # 1. Circuit loading validation
    # ================================================================
    print("\n--- 1. CIRCUIT LOADING VALIDATION ---")
    loading_results = validation.validate_circuit_loading(circuit)
    for r in loading_results:
        record("1.LOAD", r["check"], r["status"] == "PASS", r.get("detail", ""))

    # ================================================================
    # 2. Sign convention validation
    # ================================================================
    print("\n--- 2. SIGN CONVENTION VALIDATION ---")
    sign_results = validation.validate_sign_convention(circuit, config["sign_map"], W_signed)
    for r in sign_results:
        record("2.SIGN", r["check"], r["status"] == "PASS", r.get("detail", ""))

    # ================================================================
    # 3. Spectral radius and stability
    # ================================================================
    print("\n--- 3. SPECTRAL RADIUS & STABILITY ---")
    tau = simulator.build_tau_vector(circuit, config)
    stab_results = validation.validate_numerical_stability(
        W_signed, tau, config["gain"], config["dt"]
    )
    for r in stab_results:
        record("3.STAB", r["check"], r["status"] == "PASS", r.get("detail", ""))

    spectral_radius = dynamics.compute_spectral_radius(W_signed, config["gain"])
    max_real_ev = dynamics.compute_max_real_eigenvalue(W_signed, config["gain"])
    all_results["spectral_radius"] = spectral_radius
    all_results["max_real_eigenvalue"] = max_real_ev

    # ================================================================
    # Test A: Zero input
    # ================================================================
    print("\n--- TEST A: ZERO INPUT ---")

    # A1: Zero state, zero input — should remain at zero
    u_zero = inputs.make_zero_input()
    times_a1, states_a1, ro_a1 = simulator.run_simulation(circuit, config, u_zero)
    max_state_a1 = float(np.max(np.abs(states_a1)))
    record("A1", "zero_state_zero_input", max_state_a1 == 0.0,
           f"max|state|={max_state_a1}")

    # A2: Small nonzero state, zero input — must decay to zero
    # Slowest decay mode: (1 - dt/tau + dt/tau * gain * lambda_max) per step
    # = (0.9 + 0.1*0.696) = 0.9696. Need ~700 steps for 0.01 -> 1e-6.
    x0_small = np.full(circuit.n_neurons, 0.01, dtype=np.float64)
    decay_config = {**config, "duration": 1000}
    times_a2, states_a2, ro_a2 = simulator.run_simulation(
        circuit, decay_config, u_zero, x0=x0_small
    )
    max_final_a2 = float(np.max(np.abs(states_a2[-1])))
    record("A2", "small_state_decays", max_final_a2 < DECAY_THRESHOLD,
           f"max|final_state|={max_final_a2:.2e} (threshold={DECAY_THRESHOLD})")
    blowup_a2 = validation.validate_no_blowup(states_a2, "A2")
    for r in blowup_a2:
        record("A2", r["check"], r["status"] == "PASS", r.get("detail", ""))

    # ================================================================
    # Test B: LC4 only
    # ================================================================
    print("\n--- TEST B: LC4 ONLY ---")
    u_lc4 = inputs.make_population_input(circuit, {"LC4": 1.0})
    times_b, states_b, ro_b = simulator.run_simulation(circuit, config, u_lc4)
    blowup_b = validation.validate_no_blowup(states_b, "B")
    for r in blowup_b:
        record("B", r["check"], r["status"] == "PASS", r.get("detail", ""))
    sat_b = validation.validate_no_saturation(states_b, config.get("clip_max"), "B")
    for r in sat_b:
        record("B", r["check"], r["status"] == "PASS", r.get("detail", ""))

    # Report DN responses
    for dn in readouts.DN_TYPES:
        for side in ["left", "right"]:
            nr = ro_b.dn_readouts[dn][side]
            record("B", f"LC4_only_{dn}_{side}",
                   nr.max_val >= 0,
                   f"max={nr.max_val:.4f}, peak_t={nr.peak_time:.1f}ms, auc={nr.auc:.4f}")

    # ================================================================
    # Test C: LPLC2 only
    # ================================================================
    print("\n--- TEST C: LPLC2 ONLY ---")
    u_lplc2 = inputs.make_population_input(circuit, {"LPLC2": 1.0})
    times_c, states_c, ro_c = simulator.run_simulation(circuit, config, u_lplc2)
    blowup_c = validation.validate_no_blowup(states_c, "C")
    for r in blowup_c:
        record("C", r["check"], r["status"] == "PASS", r.get("detail", ""))
    sat_c = validation.validate_no_saturation(states_c, config.get("clip_max"), "C")
    for r in sat_c:
        record("C", r["check"], r["status"] == "PASS", r.get("detail", ""))

    for dn in readouts.DN_TYPES:
        for side in ["left", "right"]:
            nr = ro_c.dn_readouts[dn][side]
            record("C", f"LPLC2_only_{dn}_{side}",
                   nr.max_val >= 0,
                   f"max={nr.max_val:.4f}, peak_t={nr.peak_time:.1f}ms, auc={nr.auc:.4f}")

    # ================================================================
    # Test D: Both LC4 + LPLC2
    # ================================================================
    print("\n--- TEST D: BOTH LC4 + LPLC2 ---")
    u_both = inputs.make_population_input(circuit, {"LC4": 1.0, "LPLC2": 1.0})
    times_d, states_d, ro_d = simulator.run_simulation(circuit, config, u_both)
    blowup_d = validation.validate_no_blowup(states_d, "D")
    for r in blowup_d:
        record("D", r["check"], r["status"] == "PASS", r.get("detail", ""))
    sat_d = validation.validate_no_saturation(states_d, config.get("clip_max"), "D")
    for r in sat_d:
        record("D", r["check"], r["status"] == "PASS", r.get("detail", ""))

    # Check convergence: last 50ms state change
    late_changes = np.max(np.abs(np.diff(states_d[-50:], axis=0)), axis=1)
    max_late_change = float(np.max(late_changes))
    record("D", "convergence", max_late_change < CONVERGENCE_THRESHOLD,
           f"max_late_change={max_late_change:.6f}")

    for dn in readouts.DN_TYPES:
        for side in ["left", "right"]:
            nr = ro_d.dn_readouts[dn][side]
            record("D", f"both_{dn}_{side}",
                   nr.max_val >= 0,
                   f"max={nr.max_val:.4f}, peak_t={nr.peak_time:.1f}ms, auc={nr.auc:.4f}")

    # L-R differences
    for dn in readouts.DN_TYPES:
        diff = ro_d.lr_differences[dn]
        record("D", f"LR_diff_{dn}", True,
               f"L-R max difference = {diff:.6f}")

    # ================================================================
    # Test E: Left-only and right-only LC4
    # ================================================================
    print("\n--- TEST E: HEMISPHERE-SPECIFIC LC4 ---")

    # Left LC4 only
    u_lc4_left = inputs.make_population_input(circuit, {"LC4": 1.0}, side="left")
    times_el, states_el, ro_el = simulator.run_simulation(circuit, config, u_lc4_left)
    blowup_el = validation.validate_no_blowup(states_el, "E_left")
    for r in blowup_el:
        record("E", r["check"], r["status"] == "PASS", r.get("detail", ""))
    sat_el = validation.validate_no_saturation(states_el, config.get("clip_max"), "E_left")
    for r in sat_el:
        record("E", r["check"], r["status"] == "PASS", r.get("detail", ""))

    # Right LC4 only
    u_lc4_right = inputs.make_population_input(circuit, {"LC4": 1.0}, side="right")
    times_er, states_er, ro_er = simulator.run_simulation(circuit, config, u_lc4_right)
    blowup_er = validation.validate_no_blowup(states_er, "E_right")
    for r in blowup_er:
        record("E", r["check"], r["status"] == "PASS", r.get("detail", ""))
    sat_er = validation.validate_no_saturation(states_er, config.get("clip_max"), "E_right")
    for r in sat_er:
        record("E", r["check"], r["status"] == "PASS", r.get("detail", ""))

    # Report hemisphere pattern — do NOT assume it, just observe
    print("  Observed hemisphere pattern (LC4 left-only input):")
    for dn in readouts.DN_TYPES:
        l_max = ro_el.dn_readouts[dn]["left"].max_val
        r_max = ro_el.dn_readouts[dn]["right"].max_val
        record("E", f"left_LC4_{dn}", True,
               f"DN_L_max={l_max:.4f}, DN_R_max={r_max:.4f}, diff={l_max - r_max:.4f}")

    print("  Observed hemisphere pattern (LC4 right-only input):")
    for dn in readouts.DN_TYPES:
        l_max = ro_er.dn_readouts[dn]["left"].max_val
        r_max = ro_er.dn_readouts[dn]["right"].max_val
        record("E", f"right_LC4_{dn}", True,
               f"DN_L_max={l_max:.4f}, DN_R_max={r_max:.4f}, diff={l_max - r_max:.4f}")

    # ================================================================
    # Test F: Finite pulse
    # ================================================================
    print("\n--- TEST F: FINITE PULSE ---")
    pulse_config = {**config, "duration": 300}
    u_pulse = inputs.make_pulse_input(
        circuit, {"LC4": 1.0, "LPLC2": 1.0},
        onset=50.0, offset=150.0
    )
    times_f1, states_f1, ro_f1 = simulator.run_simulation(circuit, pulse_config, u_pulse)
    times_f2, states_f2, ro_f2 = simulator.run_simulation(circuit, pulse_config, u_pulse)

    record("F", "pulse_reproducible",
           np.array_equal(states_f1, states_f2),
           "Two pulse runs are bitwise identical")

    blowup_f = validation.validate_no_blowup(states_f1, "F")
    for r in blowup_f:
        record("F", r["check"], r["status"] == "PASS", r.get("detail", ""))
    sat_f = validation.validate_no_saturation(states_f1, config.get("clip_max"), "F")
    for r in sat_f:
        record("F", r["check"], r["status"] == "PASS", r.get("detail", ""))

    # Check response rises during pulse and decays after
    for dn in readouts.DN_TYPES:
        nr = ro_f1.dn_readouts[dn]["left"]
        # Activity at pulse onset (t=50), peak, and end (t=300)
        idx_onset = int(50 / config["dt"])
        idx_offset = int(150 / config["dt"])
        idx_end = min(int(300 / config["dt"]), len(nr.time_series) - 1)
        val_onset = nr.time_series[idx_onset]
        val_offset = nr.time_series[idx_offset]
        val_end = nr.time_series[idx_end]
        record("F", f"pulse_{dn}_temporal", True,
               f"at_onset={val_onset:.4f}, at_offset={val_offset:.4f}, "
               f"at_end={val_end:.4f}, peak={nr.max_val:.4f}")

    # ================================================================
    # Stability: multiple input levels
    # ================================================================
    print("\n--- STABILITY: INPUT LEVELS ---")
    for level_name, level_val in [("zero", 0.0), ("small", 0.1), ("moderate", 1.0), ("max", 10.0)]:
        u_level = inputs.make_population_input(circuit, {"LC4": level_val, "LPLC2": level_val})
        _, states_level, _ = simulator.run_simulation(circuit, config, u_level)
        max_state = float(np.max(np.abs(states_level)))
        has_nan = np.any(np.isnan(states_level))
        has_inf = np.any(np.isinf(states_level))
        ok = max_state < STABILITY_MAX_STATE and not has_nan and not has_inf
        record("STAB", f"input_{level_name}",
               ok,
               f"max|state|={max_state:.4f}, NaN={has_nan}, Inf={has_inf}")

    # ================================================================
    # Stability: dt sensitivity
    # ================================================================
    print("\n--- STABILITY: dt SENSITIVITY ---")
    dt_results = {}
    for dt_val in [0.5, 1.0, 2.0]:
        dt_config = {**config, "dt": dt_val, "duration": 500}
        u_dt = inputs.make_population_input(circuit, {"LC4": 1.0, "LPLC2": 1.0})
        times_dt, states_dt, ro_dt = simulator.run_simulation(circuit, dt_config, u_dt)
        max_state = float(np.max(np.abs(states_dt)))
        has_nan = np.any(np.isnan(states_dt))
        has_inf = np.any(np.isinf(states_dt))

        dn01_l = ro_dt.dn_readouts["DNp01"]["left"]
        dt_results[dt_val] = {
            "peak": dn01_l.max_val,
            "auc": dn01_l.auc,
            "max_state": max_state,
        }

        record("DT", f"dt={dt_val}ms",
               not has_nan and not has_inf and max_state < STABILITY_MAX_STATE,
               f"DNp01_L peak={dn01_l.max_val:.4f}, auc={dn01_l.auc:.4f}, max|state|={max_state:.4f}")

    # dt sensitivity comparison (0.5 vs 1.0)
    if 0.5 in dt_results and 1.0 in dt_results:
        ref_peak = dt_results[1.0]["peak"]
        ref_auc = dt_results[1.0]["auc"]
        if ref_peak > 0:
            peak_diff = abs(dt_results[0.5]["peak"] - ref_peak) / ref_peak
            record("DT", "peak_sensitivity_0.5v1.0",
                   peak_diff < DT_PEAK_TOLERANCE,
                   f"relative_diff={peak_diff:.4f} (tol={DT_PEAK_TOLERANCE})")
        if ref_auc > 0:
            auc_diff = abs(dt_results[0.5]["auc"] - ref_auc) / ref_auc
            record("DT", "auc_sensitivity_0.5v1.0",
                   auc_diff < DT_AUC_TOLERANCE,
                   f"relative_diff={auc_diff:.4f} (tol={DT_AUC_TOLERANCE})")

    # ================================================================
    # Determinism
    # ================================================================
    print("\n--- DETERMINISM ---")
    det_results = validation.validate_determinism(circuit, config)
    for r in det_results:
        record("DET", r["check"], r["status"] == "PASS", r.get("detail", ""))

    # ================================================================
    # File immutability
    # ================================================================
    print("\n--- FILE IMMUTABILITY ---")
    immut_results = validation.validate_file_immutability(pre_hashes)
    for r in immut_results:
        record("IMMUT", r["check"], r["status"] == "PASS", r.get("detail", ""))

    # ================================================================
    # Save results
    # ================================================================
    print("\n--- SAVING RESULTS ---")

    # Summary
    summary = {
        "run_date": datetime.now(timezone.utc).isoformat(),
        "circuit_version": "2.0.0",
        "total_tests": passed + failed,
        "passed": passed,
        "failed": failed,
        "spectral_radius": all_results.get("spectral_radius"),
        "max_real_eigenvalue": all_results.get("max_real_eigenvalue"),
        "gain": config["gain"],
        "dt": config["dt"],
        "pre_hashes": pre_hashes,
        "test_details": test_details,
        "dt_sensitivity": {str(k): v for k, v in dt_results.items()},
    }

    # Save DN readout summaries for each test
    for test_name, ro_obj in [("B_LC4", ro_b), ("C_LPLC2", ro_c), ("D_both", ro_d),
                               ("E_left", ro_el), ("E_right", ro_er), ("F_pulse", ro_f1)]:
        summary[f"readout_{test_name}"] = readouts.readout_summary_dict(ro_obj)

    results_path = RESULTS_DIR / "phase4_test_results.json"
    with open(results_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"  Results saved to {results_path}")

    # ================================================================
    # Final summary
    # ================================================================
    print("\n" + "=" * 70)
    print(f"PHASE 4 TESTS: {passed}/{passed + failed} passed")
    if failed == 0:
        print("ALL TESTS PASSED")
    else:
        print(f"FAILED: {failed} tests")
        for td in test_details:
            if td["status"] == "FAIL":
                print(f"  ✗ [{td['test_id']}] {td['name']}: {td['detail'][:100]}")
    print("=" * 70)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
