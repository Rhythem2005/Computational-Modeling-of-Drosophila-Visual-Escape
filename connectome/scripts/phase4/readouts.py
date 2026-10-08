"""Readout extraction for Phase 4 simulation.

Extracts per-neuron, L/R, and population time series from simulation states.
Readouts: DNp01 (primary), DNp04/DNp02/DNp11/DNp06 (secondary).
No behavior mapping — just activity reporting.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from . import loader


DN_TYPES = ["DNp01", "DNp04", "DNp02", "DNp11", "DNp06"]
PRIMARY_DN = "DNp01"
SECONDARY_DNS = ["DNp04", "DNp02", "DNp11", "DNp06"]
INPUT_TYPES = ["LC4", "LPLC2"]
ALL_POPULATIONS = INPUT_TYPES + DN_TYPES
SIDES = ["left", "right"]


@dataclass
class NeuronReadout:
    """Readout for a single neuron."""
    body_id: int
    neuron_type: str
    side: str
    time_series: np.ndarray  # [n_steps + 1]
    mean: float = 0.0
    max_val: float = 0.0
    peak_time: float = 0.0
    auc: float = 0.0

    def compute_stats(self, times: np.ndarray, dt: float) -> None:
        """Compute summary statistics from time series."""
        self.mean = float(np.mean(self.time_series))
        self.max_val = float(np.max(self.time_series))
        if len(self.time_series) > 0:
            self.peak_time = float(times[np.argmax(self.time_series)])
        self.auc = float(np.trapezoid(self.time_series, times))


@dataclass
class PopulationReadout:
    """Readout for a population (e.g., DNp01_left, LC4_right)."""
    population: str
    side: str
    neuron_readouts: list[NeuronReadout] = field(default_factory=list)
    mean_activity: np.ndarray = field(default_factory=lambda: np.array([]))
    mean_of_mean: float = 0.0
    max_of_max: float = 0.0
    mean_peak_time: float = 0.0
    mean_auc: float = 0.0

    def compute_stats(self, times: np.ndarray, dt: float) -> None:
        """Compute population-level statistics."""
        if not self.neuron_readouts:
            return
        all_ts = np.array([nr.time_series for nr in self.neuron_readouts])
        self.mean_activity = np.mean(all_ts, axis=0)
        self.mean_of_mean = float(np.mean([nr.mean for nr in self.neuron_readouts]))
        self.max_of_max = float(np.max([nr.max_val for nr in self.neuron_readouts]))
        peak_times = [nr.peak_time for nr in self.neuron_readouts]
        self.mean_peak_time = float(np.mean(peak_times)) if peak_times else 0.0
        self.mean_auc = float(np.mean([nr.auc for nr in self.neuron_readouts]))


@dataclass
class SimulationReadout:
    """Complete readout from a simulation run."""
    dn_readouts: dict[str, dict[str, NeuronReadout]] = field(default_factory=dict)
    # dn_readouts[dn_type][side] -> NeuronReadout
    population_readouts: dict[str, dict[str, PopulationReadout]] = field(default_factory=dict)
    # population_readouts[pop_name][side] -> PopulationReadout
    lr_differences: dict[str, float] = field(default_factory=dict)
    # lr_differences[dn_type] -> max(left) - max(right)


def extract_readouts(
    circuit: loader.CircuitData,
    times: np.ndarray,
    states: np.ndarray,
    dt: float,
) -> SimulationReadout:
    """Extract all readouts from simulation results.

    Args:
        circuit: Loaded circuit data.
        times: Time array [n_steps + 1].
        states: State array [n_steps + 1, n_neurons].
        dt: Time step used in simulation.

    Returns:
        SimulationReadout with per-neuron, population, and L-R difference data.
    """
    readout = SimulationReadout()

    # Extract DN readouts (per-neuron, L/R)
    for dn_type in DN_TYPES:
        readout.dn_readouts[dn_type] = {}
        for side in SIDES:
            bid = circuit.get_dn_body_id(dn_type, side)
            idx = circuit.id_to_idx[bid]
            ts = states[:, idx].copy()
            nr = NeuronReadout(
                body_id=bid,
                neuron_type=dn_type,
                side=side,
                time_series=ts,
            )
            nr.compute_stats(times, dt)
            readout.dn_readouts[dn_type][side] = nr

    # Extract population readouts for all populations
    for pop_name in ALL_POPULATIONS:
        readout.population_readouts[pop_name] = {}
        for side in SIDES:
            bids = circuit.get_population_body_ids(pop_name, side=side)
            neuron_readouts = []
            for bid in bids:
                idx = circuit.id_to_idx[bid]
                ts = states[:, idx].copy()
                nr = NeuronReadout(
                    body_id=bid,
                    neuron_type=pop_name,
                    side=side,
                    time_series=ts,
                )
                nr.compute_stats(times, dt)
                neuron_readouts.append(nr)
            pr = PopulationReadout(
                population=pop_name,
                side=side,
                neuron_readouts=neuron_readouts,
            )
            pr.compute_stats(times, dt)
            readout.population_readouts[pop_name][side] = pr

    # Compute L-R differences for DNs
    for dn_type in DN_TYPES:
        left_max = readout.dn_readouts[dn_type]["left"].max_val
        right_max = readout.dn_readouts[dn_type]["right"].max_val
        readout.lr_differences[dn_type] = left_max - right_max

    return readout


def readout_summary_dict(readout: SimulationReadout) -> dict:
    """Convert readout to a serializable dictionary."""
    result = {"dn_neurons": {}, "lr_differences": readout.lr_differences}
    for dn_type in DN_TYPES:
        result["dn_neurons"][dn_type] = {}
        for side in SIDES:
            nr = readout.dn_readouts[dn_type][side]
            result["dn_neurons"][dn_type][side] = {
                "body_id": nr.body_id,
                "mean": round(nr.mean, 6),
                "max": round(nr.max_val, 6),
                "peak_time_ms": round(nr.peak_time, 2),
                "auc": round(nr.auc, 4),
            }
    return result
