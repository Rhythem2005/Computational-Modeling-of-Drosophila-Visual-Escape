"""Reproducible Phase 4 integration and validation suite.

Run from the project root:
    ./venv/bin/python connectome/scripts/phase4/run_phase4_tests.py

The suite writes machine-readable evidence to
``connectome/phase4/results/phase4_test_results.json`` and never modifies
Phase 3 artifacts.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from connectome.scripts.phase4 import dynamics, inputs, loader, readouts, simulator, validation

PHASE4_DIR = PROJECT_ROOT / "connectome" / "phase4"
RESULTS_DIR = PHASE4_DIR / "results"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative_error(value: float, reference: float, floor: float = 1e-12) -> float:
    return abs(value - reference) / max(abs(reference), floor)


def main() -> int:
    run_time = datetime.now(timezone.utc).isoformat()
    print("=" * 72)
    print("PHASE 4 — RATE-MODEL INTEGRATION AND VALIDATION")
    print(f"Run date: {run_time}")
    print("=" * 72)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    passed = 0
    failed = 0
    test_details: list[dict] = []

    def record(test_id: str, name: str, ok: bool | None, detail: str = "") -> None:
        nonlocal passed, failed
        if ok is None:
            status, icon = "INFO", "i"
        elif bool(ok):
            status, icon = "PASS", "✓"
            passed += 1
        else:
            status, icon = "FAIL", "✗"
            failed += 1
        test_details.append({"test_id": test_id, "name": name, "status": status, "detail": detail})
        print(f"  {icon} [{test_id}] {name}: {detail[:180]}")

    print("\n--- 0. LOAD FROZEN CIRCUIT AND CONFIGURATION ---")
    start = time.perf_counter()
    circuit = loader.load_circuit()
    config = simulator.load_config()
    load_seconds = time.perf_counter() - start
    pre_hashes = circuit.file_hashes.copy()
    W_signed = loader.build_signed_weight_matrix(circuit, config["sign_map"])
    tau = simulator.build_tau_vector(circuit, config)
    print(
        f"  Loaded {circuit.n_neurons} neurons and {len(circuit.edges_df)} edges "
        f"in {load_seconds:.3f}s"
    )

    print("\n--- 1. CIRCUIT CONTRACT ---")
    for result in validation.validate_circuit_loading(circuit):
        record("LOAD", result["check"], result["status"] == "PASS", result.get("detail", ""))

    print("\n--- 2. SYNAPTIC SIGN CONVENTION ---")
    for result in validation.validate_sign_convention(circuit, config["sign_map"], W_signed):
        record("SIGN", result["check"], result["status"] == "PASS", result.get("detail", ""))

    print("\n--- 3. MATHEMATICAL STABILITY ---")
    stability_results = validation.validate_numerical_stability(
        W_signed, tau, config["gain"], config["dt"]
    )
    for result in stability_results:
        record("MATH", result["check"], result["status"] == "PASS", result.get("detail", ""))
    spectral_radius = dynamics.compute_spectral_radius(W_signed, config["gain"])
    max_real_eigenvalue = dynamics.compute_max_real_eigenvalue(W_signed, config["gain"])

    response_floor = float(config["response_floor"])
    convergence_tolerance = float(config["convergence_step_tolerance"])

    print("\n--- A. ZERO INPUT ---")
    zero_input = inputs.make_zero_input()
    _, zero_states, _ = simulator.run_simulation(circuit, config, zero_input)
    record("A1", "zero_fixed_point", np.array_equal(zero_states, np.zeros_like(zero_states)),
           f"max_abs={np.max(np.abs(zero_states)):.3e}")

    decay_config = {**config, "duration": 1000.0}
    initial_state = np.full(circuit.n_neurons, 0.01, dtype=np.float64)
    decay_times, decay_states, _ = simulator.run_simulation(
        circuit, decay_config, zero_input, x0=initial_state
    )
    below = np.flatnonzero(np.max(np.abs(decay_states), axis=1) < 1e-6)
    decay_time = float(decay_times[below[0]]) if below.size else None
    record("A2", "perturbation_decays_below_1e-6", decay_time is not None,
           f"decay_time_ms={decay_time}; final_max_abs={np.max(np.abs(decay_states[-1])):.3e}")
    for result in validation.validate_no_blowup(decay_states, "A2"):
        record("A2", result["check"], result["status"] == "PASS", result.get("detail", ""))

    scenario_outputs: dict[str, tuple[np.ndarray, np.ndarray, readouts.SimulationReadout]] = {}
    scenarios = {
        "B_LC4": inputs.make_population_input(circuit, {"LC4": 1.0}),
        "C_LPLC2": inputs.make_population_input(circuit, {"LPLC2": 1.0}),
        "D_both": inputs.make_population_input(circuit, {"LC4": 1.0, "LPLC2": 1.0}),
    }
    for scenario, input_function in scenarios.items():
        print(f"\n--- {scenario} ---")
        times, states, simulation_readout = simulator.run_simulation(circuit, config, input_function)
        scenario_outputs[scenario] = (times, states, simulation_readout)
        for result in validation.validate_no_blowup(states, scenario):
            record(scenario, result["check"], result["status"] == "PASS", result.get("detail", ""))
        for result in validation.validate_no_saturation(
            states, config.get("clip_max"), scenario, dt=config["dt"]
        ):
            record(scenario, result["check"], result["status"] == "PASS", result.get("detail", ""))
        for dn_type in readouts.DN_TYPES:
            for side in readouts.SIDES:
                neuron = simulation_readout.dn_readouts[dn_type][side]
                ok = neuron.max_val > response_floor and np.isfinite(neuron.t90)
                record(
                    scenario,
                    f"{dn_type}_{side}_sustained_response",
                    ok,
                    f"max={neuron.max_val:.6f}, steady={neuron.steady_state:.6f}, "
                    f"t90_ms={neuron.t90:.1f}, auc={neuron.auc:.4f}",
                )

    both_states = scenario_outputs["D_both"][1]
    late_window_steps = max(2, int(round(50.0 / config["dt"])))
    max_late_change = float(np.max(np.abs(np.diff(both_states[-late_window_steps:], axis=0))))
    record("D_both", "converged_over_final_50ms", max_late_change < convergence_tolerance,
           f"max_step_change={max_late_change:.9f}; tolerance={convergence_tolerance}")

    print("\n--- E. HEMISPHERE-SPECIFIC LC4 ---")
    hemisphere_outputs = {}
    for side in readouts.SIDES:
        side_input = inputs.make_population_input(circuit, {"LC4": 1.0}, side=side)
        times, states, simulation_readout = simulator.run_simulation(circuit, config, side_input)
        hemisphere_outputs[side] = (times, states, simulation_readout)
        for result in validation.validate_no_blowup(states, f"E_{side}"):
            record("E", result["check"], result["status"] == "PASS", result.get("detail", ""))
        for result in validation.validate_no_saturation(
            states, config.get("clip_max"), f"E_{side}", dt=config["dt"]
        ):
            record("E", result["check"], result["status"] == "PASS", result.get("detail", ""))
        for dn_type in readouts.DN_TYPES:
            left_max = simulation_readout.dn_readouts[dn_type]["left"].max_val
            right_max = simulation_readout.dn_readouts[dn_type]["right"].max_val
            record("E", f"{side}_input_{dn_type}_lr_observation", None,
                   f"left_max={left_max:.6f}, right_max={right_max:.6f}, difference={left_max-right_max:.6f}")
    left_dn = np.asarray([
        hemisphere_outputs["left"][2].dn_readouts[dn][side].max_val
        for dn in readouts.DN_TYPES for side in readouts.SIDES
    ])
    right_dn = np.asarray([
        hemisphere_outputs["right"][2].dn_readouts[dn][side].max_val
        for dn in readouts.DN_TYPES for side in readouts.SIDES
    ])
    record("E", "hemisphere_inputs_produce_distinct_dn_vectors",
           not np.allclose(left_dn, right_dn, rtol=1e-10, atol=1e-12),
           f"max_abs_vector_difference={np.max(np.abs(left_dn-right_dn)):.6f}")

    print("\n--- F. FINITE PULSE ---")
    pulse_config = {**config, "duration": 300.0}
    pulse_input = inputs.make_pulse_input(
        circuit, {"LC4": 1.0, "LPLC2": 1.0}, onset=50.0, offset=150.0
    )
    pulse_times, pulse_states, pulse_readout = simulator.run_simulation(
        circuit, pulse_config, pulse_input
    )
    _, repeated_states, _ = simulator.run_simulation(circuit, pulse_config, pulse_input)
    record("F", "bitwise_reproducible", np.array_equal(pulse_states, repeated_states),
           "two pulse simulations are bitwise identical")
    for result in validation.validate_no_blowup(pulse_states, "F"):
        record("F", result["check"], result["status"] == "PASS", result.get("detail", ""))
    for result in validation.validate_no_saturation(
        pulse_states, config.get("clip_max"), "F", dt=config["dt"]
    ):
        record("F", result["check"], result["status"] == "PASS", result.get("detail", ""))
    residual_tolerance = float(config["pulse_residual_fraction_tolerance"])
    for dn_type in readouts.DN_TYPES:
        for side in readouts.SIDES:
            neuron = pulse_readout.dn_readouts[dn_type][side]
            residual_fraction = neuron.steady_state / max(neuron.max_val, 1e-12)
            peak_in_window = 50.0 < neuron.peak_time <= 175.0
            ok = (
                neuron.max_val > response_floor
                and peak_in_window
                and residual_fraction < residual_tolerance
                and np.isnan(neuron.t90)
            )
            record("F", f"{dn_type}_{side}_pulse_response", ok,
                   f"peak={neuron.max_val:.6f} at {neuron.peak_time:.1f}ms; "
                   f"end={neuron.steady_state:.6f}; residual_fraction={residual_fraction:.6f}; t90=undefined")

    print("\n--- STRESS AND CLIPPING BEHAVIOR ---")
    stress_input = inputs.make_population_input(circuit, {"LC4": 10.0, "LPLC2": 10.0})
    unclipped_config = {**config, "clip_max": None}
    _, stress_states, _ = simulator.run_simulation(circuit, unclipped_config, stress_input)
    stress_max = float(np.max(stress_states))
    record("STRESS", "high_input_unclipped_is_finite",
           np.all(np.isfinite(stress_states)) and stress_max < 1e5,
           f"max_activity={stress_max:.6f}")
    _, clipped_states, _ = simulator.run_simulation(circuit, config, stress_input)
    clipped_max = float(np.max(clipped_states))
    record("STRESS", "configured_clip_bounds_high_input", clipped_max <= config["clip_max"] + 1e-12,
           f"max_activity={clipped_max:.6f}; clip_max={config['clip_max']}")
    record("STRESS", "high_input_reaches_configured_clip", None,
           f"clip is active outside the normal operating range: {np.isclose(clipped_max, config['clip_max'])}")

    print("\n--- TIMESTEP SENSITIVITY ---")
    dt_values = [float(value) for value in config["dt_values_ms"]]
    if 1.0 not in dt_values:
        raise ValueError("dt_values_ms must include the 1.0 ms reference")
    dt_results: dict[str, dict] = {}
    for dt_value in dt_values:
        dt_config = {**config, "dt": dt_value}
        dt_results[str(dt_value)] = {}
        for scenario, input_function in scenarios.items():
            _, states, ro = simulator.run_simulation(circuit, dt_config, input_function)
            dt_results[str(dt_value)][scenario] = {
                f"{dn}_{side}": {
                    "steady_state": ro.dn_readouts[dn][side].steady_state,
                    "auc": ro.dn_readouts[dn][side].auc,
                    "t90_ms": ro.dn_readouts[dn][side].t90,
                }
                for dn in readouts.DN_TYPES for side in readouts.SIDES
            }
            record("DT", f"{scenario}_dt_{dt_value:g}ms_finite", np.all(np.isfinite(states)),
                   f"max_activity={np.max(states):.6f}")
        dt_pulse_config = {**dt_config, "duration": 300.0}
        _, states, ro = simulator.run_simulation(circuit, dt_pulse_config, pulse_input)
        dt_results[str(dt_value)]["F_pulse"] = {
            f"{dn}_{side}": {
                "peak": ro.dn_readouts[dn][side].max_val,
                "auc": ro.dn_readouts[dn][side].auc,
                "end": ro.dn_readouts[dn][side].steady_state,
            }
            for dn in readouts.DN_TYPES for side in readouts.SIDES
        }
        record("DT", f"F_pulse_dt_{dt_value:g}ms_finite", np.all(np.isfinite(states)),
               f"max_activity={np.max(states):.6f}")

    response_tolerance = float(config["dt_response_tolerance"])
    auc_tolerance = float(config["dt_auc_tolerance"])
    reference = dt_results["1.0"]
    dt_comparisons = {}
    for dt_value in dt_values:
        if dt_value == 1.0:
            continue
        current = dt_results[str(dt_value)]
        dt_comparisons[str(dt_value)] = {}
        for scenario in scenarios:
            response_errors, auc_errors, t90_errors = [], [], []
            for neuron_name, metrics in current[scenario].items():
                reference_metrics = reference[scenario][neuron_name]
                response_errors.append(_relative_error(metrics["steady_state"], reference_metrics["steady_state"]))
                auc_errors.append(_relative_error(metrics["auc"], reference_metrics["auc"]))
                t90_errors.append(abs(metrics["t90_ms"] - reference_metrics["t90_ms"]))
            worst_response, worst_auc, worst_t90 = max(response_errors), max(auc_errors), max(t90_errors)
            dt_comparisons[str(dt_value)][scenario] = {
                "worst_response_relative_error": worst_response,
                "worst_auc_relative_error": worst_auc,
                "worst_t90_absolute_error_ms": worst_t90,
            }
            record("DT", f"{scenario}_{dt_value:g}ms_response_sensitivity",
                   worst_response <= response_tolerance,
                   f"worst_relative_error={worst_response:.6f}; tolerance={response_tolerance}")
            record("DT", f"{scenario}_{dt_value:g}ms_auc_sensitivity", worst_auc <= auc_tolerance,
                   f"worst_relative_error={worst_auc:.6f}; tolerance={auc_tolerance}")
            record("DT", f"{scenario}_{dt_value:g}ms_t90_quantization", worst_t90 <= dt_value + 1.0,
                   f"worst_absolute_error_ms={worst_t90:.3f}; tolerance={dt_value + 1.0:.3f}")
        peak_errors, auc_errors = [], []
        for neuron_name, metrics in current["F_pulse"].items():
            reference_metrics = reference["F_pulse"][neuron_name]
            peak_errors.append(_relative_error(metrics["peak"], reference_metrics["peak"]))
            auc_errors.append(_relative_error(metrics["auc"], reference_metrics["auc"]))
        worst_peak, worst_auc = max(peak_errors), max(auc_errors)
        dt_comparisons[str(dt_value)]["F_pulse"] = {
            "worst_peak_relative_error": worst_peak,
            "worst_auc_relative_error": worst_auc,
        }
        record("DT", f"F_pulse_{dt_value:g}ms_peak_sensitivity", worst_peak <= response_tolerance,
               f"worst_relative_error={worst_peak:.6f}; tolerance={response_tolerance}")
        record("DT", f"F_pulse_{dt_value:g}ms_auc_sensitivity", worst_auc <= auc_tolerance,
               f"worst_relative_error={worst_auc:.6f}; tolerance={auc_tolerance}")

    print("\n--- DETERMINISM AND PHASE 3 IMMUTABILITY ---")
    for result in validation.validate_determinism(circuit, config):
        record("DET", result["check"], result["status"] == "PASS", result.get("detail", ""))
    for result in validation.validate_file_immutability(pre_hashes):
        record("IMMUT", result["check"], result["status"] == "PASS", result.get("detail", ""))

    scenario_summaries = {
        scenario: readouts.readout_summary_dict(output[2])
        for scenario, output in scenario_outputs.items()
    }
    scenario_summaries["E_left"] = readouts.readout_summary_dict(hemisphere_outputs["left"][2])
    scenario_summaries["E_right"] = readouts.readout_summary_dict(hemisphere_outputs["right"][2])
    scenario_summaries["F_pulse"] = readouts.readout_summary_dict(pulse_readout)

    summary = {
        "schema_version": "2.0",
        "run_date": run_time,
        "circuit_version": "2.0.0",
        "status": "PASS" if failed == 0 else "FAIL",
        "assertions": {"total": passed + failed, "passed": passed, "failed": failed},
        "informational_records": sum(item["status"] == "INFO" for item in test_details),
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "platform": platform.platform(),
        },
        "config_sha256": _sha256(PHASE4_DIR / "simulation_config.yaml"),
        "phase3_hashes": pre_hashes,
        "spectral_radius_gain_times_W": spectral_radius,
        "max_real_eigenvalue_gain_times_W": max_real_eigenvalue,
        "test_details": test_details,
        "dt_sensitivity": dt_results,
        "dt_comparisons": dt_comparisons,
        "readouts": scenario_summaries,
    }
    results_path = RESULTS_DIR / "phase4_test_results.json"
    with results_path.open("w") as handle:
        json.dump(summary, handle, indent=2, allow_nan=False)

    print("\n" + "=" * 72)
    print(f"PHASE 4 ASSERTIONS: {passed}/{passed + failed} passed; {failed} failed")
    print(f"Machine-readable evidence: {results_path}")
    print("=" * 72)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
