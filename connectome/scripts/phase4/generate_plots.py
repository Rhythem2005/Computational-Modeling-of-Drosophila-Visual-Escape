"""Generate 5 diagnostic plots for Phase 4 simulation.

Plots:
1. LC4 -> DN responses
2. LPLC2 -> DN responses
3. Both LC4+LPLC2 -> DN responses
4. L vs R asymmetric (left-only LC4 input)
5. Pulse temporal comparison

Run from project root:
    ./venv/bin/python connectome/scripts/phase4/generate_plots.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from connectome.scripts.phase4 import inputs, loader, readouts, simulator

PLOTS_DIR = PROJECT_ROOT / "connectome" / "phase4" / "reports"
DN_TYPES = readouts.DN_TYPES
DN_COLORS = {"DNp01": "#E63946", "DNp04": "#457B9D", "DNp02": "#2A9D8F",
             "DNp11": "#E9C46A", "DNp06": "#F4A261"}


def plot_dn_responses(times, ro, title, filename, label_suffix=""):
    """Plot all DN L/R responses on one figure."""
    fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    fig.suptitle(title, fontsize=13)

    for dn in DN_TYPES:
        color = DN_COLORS[dn]
        nr_l = ro.dn_readouts[dn]["left"]
        nr_r = ro.dn_readouts[dn]["right"]
        axes[0].plot(times, nr_l.time_series, color=color, label=f"{dn} L")
        axes[1].plot(times, nr_r.time_series, color=color, label=f"{dn} R", linestyle="--")

    axes[0].set_ylabel("Activity (a.u.)")
    axes[0].set_title("Left hemisphere DNs")
    axes[0].legend(fontsize=8)
    axes[0].grid(True, alpha=0.3)

    axes[1].set_ylabel("Activity (a.u.)")
    axes[1].set_xlabel("Time (ms)")
    axes[1].set_title("Right hemisphere DNs")
    axes[1].legend(fontsize=8)
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(PLOTS_DIR / filename, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {filename}")


def main():
    print("Generating Phase 4 diagnostic plots...")
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    # Load circuit and config
    circuit = loader.load_circuit()
    config = simulator.load_config()

    # === Plot 1: LC4 -> DN ===
    u_lc4 = inputs.make_population_input(circuit, {"LC4": 1.0})
    times_b, states_b, ro_b = simulator.run_simulation(circuit, config, u_lc4)
    plot_dn_responses(times_b, ro_b, "LC4 Only → DN Responses", "plot1_lc4_to_dn.png")

    # === Plot 2: LPLC2 -> DN ===
    u_lplc2 = inputs.make_population_input(circuit, {"LPLC2": 1.0})
    times_c, states_c, ro_c = simulator.run_simulation(circuit, config, u_lplc2)
    plot_dn_responses(times_c, ro_c, "LPLC2 Only → DN Responses", "plot2_lplc2_to_dn.png")

    # === Plot 3: Both LC4+LPLC2 -> DN ===
    u_both = inputs.make_population_input(circuit, {"LC4": 1.0, "LPLC2": 1.0})
    times_d, states_d, ro_d = simulator.run_simulation(circuit, config, u_both)
    plot_dn_responses(times_d, ro_d, "LC4 + LPLC2 → DN Responses", "plot3_both_to_dn.png")

    # === Plot 4: L vs R asymmetric (left-only LC4) ===
    u_lc4_left = inputs.make_population_input(circuit, {"LC4": 1.0}, side="left")
    times_el, states_el, ro_el = simulator.run_simulation(circuit, config, u_lc4_left)

    fig, ax = plt.subplots(figsize=(10, 5))
    for dn in DN_TYPES:
        color = DN_COLORS[dn]
        nr_l = ro_el.dn_readouts[dn]["left"]
        nr_r = ro_el.dn_readouts[dn]["right"]
        ax.plot(times_el, nr_l.time_series, color=color, label=f"{dn} L", linewidth=2)
        ax.plot(times_el, nr_r.time_series, color=color, label=f"{dn} R",
                linewidth=1, linestyle="--", alpha=0.7)

    ax.set_xlabel("Time (ms)")
    ax.set_ylabel("Activity (a.u.)")
    ax.set_title("Left-Only LC4 Input: L vs R DN Asymmetry")
    ax.legend(fontsize=7, ncol=2)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "plot4_lr_asymmetry.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  Saved: plot4_lr_asymmetry.png")

    # === Plot 5: Pulse temporal comparison ===
    pulse_config = {**config, "duration": 300}
    u_pulse = inputs.make_pulse_input(
        circuit, {"LC4": 1.0, "LPLC2": 1.0},
        onset=50.0, offset=150.0
    )
    times_f, states_f, ro_f = simulator.run_simulation(circuit, pulse_config, u_pulse)

    fig, ax = plt.subplots(figsize=(10, 5))
    # Shade pulse period
    ax.axvspan(50, 150, alpha=0.1, color="gray", label="Pulse on")

    for dn in DN_TYPES:
        color = DN_COLORS[dn]
        nr_l = ro_f.dn_readouts[dn]["left"]
        ax.plot(times_f, nr_l.time_series, color=color, label=f"{dn} L", linewidth=1.5)

    ax.set_xlabel("Time (ms)")
    ax.set_ylabel("Activity (a.u.)")
    ax.set_title("Pulse Input [50–150 ms]: DN Temporal Responses (Left)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "plot5_pulse_comparison.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  Saved: plot5_pulse_comparison.png")

    print("All 5 diagnostic plots generated.")


if __name__ == "__main__":
    main()
