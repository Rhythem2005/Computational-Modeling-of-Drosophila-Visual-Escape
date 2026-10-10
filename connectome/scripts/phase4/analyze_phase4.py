"""Generate reproducible scientific analyses for the Phase 4 report."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from connectome.scripts.phase4 import dynamics, inputs, loader, readouts, simulator

RESULT_PATH = PROJECT_ROOT / "connectome" / "phase4" / "results" / "analysis_data.json"


def _dn_values(circuit, simulation_readout, attribute: str) -> dict[str, float]:
    return {
        f"{dn}_{side}": float(getattr(simulation_readout.dn_readouts[dn][side], attribute))
        for dn in readouts.DN_TYPES
        for side in readouts.SIDES
    }


def _rank(values: dict[str, float]) -> list[dict[str, float | int | str]]:
    ordered = sorted(values.items(), key=lambda item: item[1], reverse=True)
    return [
        {"rank": index, "neuron": name, "steady_state": value}
        for index, (name, value) in enumerate(ordered, start=1)
    ]


def main() -> int:
    circuit = loader.load_circuit()
    config = simulator.load_config()
    edges = circuit.edges_df.copy()

    u_lc4 = inputs.make_population_input(circuit, {"LC4": 1.0})
    u_lplc2 = inputs.make_population_input(circuit, {"LPLC2": 1.0})
    u_both = inputs.make_population_input(circuit, {"LC4": 1.0, "LPLC2": 1.0})
    _, states_lc4, ro_lc4 = simulator.run_simulation(circuit, config, u_lc4)
    _, states_lplc2, ro_lplc2 = simulator.run_simulation(circuit, config, u_lplc2)
    _, states_both, ro_both = simulator.run_simulation(circuit, config, u_both)

    labels = [f"{dn}_{side}" for dn in readouts.DN_TYPES for side in readouts.SIDES]
    direct_weights = {"LC4": {}, "LPLC2": {}}
    for dn in readouts.DN_TYPES:
        for side in readouts.SIDES:
            label = f"{dn}_{side}"
            body_id = circuit.get_dn_body_id(dn, side)
            incoming = edges[edges["bodyId_post"] == body_id]
            for visual_type in ("LC4", "LPLC2"):
                direct_weights[visual_type][label] = float(
                    incoming.loc[incoming["pre_type"] == visual_type, "weight"].sum()
                )

    steady_lc4 = _dn_values(circuit, ro_lc4, "steady_state")
    steady_lplc2 = _dn_values(circuit, ro_lplc2, "steady_state")
    steady_both = _dn_values(circuit, ro_both, "steady_state")
    lc4_correlation = spearmanr(
        [direct_weights["LC4"][label] for label in labels],
        [steady_lc4[label] for label in labels],
    )
    lplc2_correlation = spearmanr(
        [direct_weights["LPLC2"][label] for label in labels],
        [steady_lplc2[label] for label in labels],
    )

    W_signed = loader.build_signed_weight_matrix(circuit, config["sign_map"])
    W_direct = W_signed.copy()
    removed_classes = ["intra_population", "cross_visual", "readout_to_visual", "inter_readout"]
    for edge in edges[edges["edge_class"].isin(removed_classes)].itertuples():
        W_direct[circuit.id_to_idx[edge.bodyId_post], circuit.id_to_idx[edge.bodyId_pre]] = 0.0
    tau = simulator.build_tau_vector(circuit, config)
    bias = simulator.build_bias_vector(circuit, config)
    scaled_both = lambda t, n: config["input_scale"] * u_both(t, n)
    _, direct_states = dynamics.simulate(
        W_direct, tau, config["gain"], config["dt"], config["duration"], scaled_both,
        b=bias, clip_max=config.get("clip_max"),
    )
    direct_vs_full = {}
    for dn in readouts.DN_TYPES:
        for side in readouts.SIDES:
            label = f"{dn}_{side}"
            idx = circuit.get_dn_index(dn, side)
            full = float(states_both[-1, idx])
            direct = float(direct_states[-1, idx])
            direct_vs_full[label] = {
                "full_steady_state": full,
                "direct_only_steady_state": direct,
                "direct_fraction": direct / full if full else None,
                "network_mediated_fraction": 1.0 - direct / full if full else None,
            }

    linearity_errors = {}
    for dn in readouts.DN_TYPES:
        for side in readouts.SIDES:
            label = f"{dn}_{side}"
            idx = circuit.get_dn_index(dn, side)
            combined = float(states_both[-1, idx])
            summed = float(states_lc4[-1, idx] + states_lplc2[-1, idx])
            linearity_errors[label] = {
                "combined": combined,
                "sum_of_separate": summed,
                "absolute_error": abs(combined - summed),
                "relative_error": abs(combined - summed) / combined if combined else 0.0,
            }

    hemisphere_results = {}
    for input_side in readouts.SIDES:
        u_side = inputs.make_population_input(circuit, {"LC4": 1.0}, side=input_side)
        _, _, ro_side = simulator.run_simulation(circuit, config, u_side)
        hemisphere_results[input_side] = _dn_values(circuit, ro_side, "steady_state")

    gain_sensitivity = {}
    for gain in config["gain_sensitivity_values"]:
        gain_config = {**config, "gain": float(gain)}
        _, gain_states, gain_readout = simulator.run_simulation(circuit, gain_config, u_both)
        values = _dn_values(circuit, gain_readout, "steady_state")
        gain_sensitivity[str(float(gain))] = {
            "spectral_radius_gain_times_W": dynamics.compute_spectral_radius(W_signed, float(gain)),
            "max_activity_all_neurons": float(np.max(gain_states)),
            "clip_reached": bool(np.max(gain_states) >= config["clip_max"] * 0.999),
            "ranking": _rank(values),
        }

    nt_counts = {str(key): int(value) for key, value in circuit.nodes_df["predicted_nt"].value_counts().items()}
    sign_edge_counts = {}
    for nt, group in edges.groupby("pre_nt"):
        sign_edge_counts[str(nt)] = {
            "assumed_sign": float(config["sign_map"][nt]),
            "edges": int(len(group)),
            "synapses": int(group["weight"].sum()),
        }

    output = {
        "schema_version": "2.0",
        "run_date": datetime.now(timezone.utc).isoformat(),
        "circuit_version": "2.0.0",
        "phase3_hashes": circuit.file_hashes,
        "neurotransmitter_predictions": nt_counts,
        "sign_mapping_by_edge": sign_edge_counts,
        "direct_visual_weights": direct_weights,
        "steady_state_responses": {
            "LC4": steady_lc4,
            "LPLC2": steady_lplc2,
            "both": steady_both,
        },
        "connectivity_response_spearman": {
            "LC4": {"rho": float(lc4_correlation.statistic), "p_value": float(lc4_correlation.pvalue), "n": 10},
            "LPLC2": {"rho": float(lplc2_correlation.statistic), "p_value": float(lplc2_correlation.pvalue), "n": 10},
        },
        "direct_only_ablation": {
            "removed_edge_classes": removed_classes,
            "readouts": direct_vs_full,
        },
        "hemisphere_specific_lc4": hemisphere_results,
        "linearity_check": {
            "explanation": "Empirical superposition check in the tested non-negative, unsaturated operating regime.",
            "readouts": linearity_errors,
            "max_absolute_error": max(item["absolute_error"] for item in linearity_errors.values()),
            "max_relative_error": max(item["relative_error"] for item in linearity_errors.values()),
        },
        "gain_sensitivity": gain_sensitivity,
    }
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RESULT_PATH.open("w") as handle:
        json.dump(output, handle, indent=2, allow_nan=False)

    print(f"Analysis written to {RESULT_PATH}")
    print(
        "Connectivity-response Spearman rho: "
        f"LC4={lc4_correlation.statistic:.4f}, LPLC2={lplc2_correlation.statistic:.4f}"
    )
    print(
        "Maximum superposition error: "
        f"{output['linearity_check']['max_absolute_error']:.3e}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
