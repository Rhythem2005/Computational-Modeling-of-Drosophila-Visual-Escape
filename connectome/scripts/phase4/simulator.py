"""High-level simulator for Phase 4.

Combines loader, dynamics, inputs, and readouts into a coherent simulation pipeline.
Loads configuration from simulation_config.yaml.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import numpy as np
import yaml

from . import dynamics, inputs, loader, readouts


CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "phase4" / "simulation_config.yaml"


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load simulation configuration from YAML."""
    if config_path is None:
        config_path = CONFIG_PATH
    with open(config_path) as f:
        return yaml.safe_load(f)


def build_tau_vector(circuit: loader.CircuitData, config: dict) -> np.ndarray:
    """Build per-neuron tau vector from config population taus.

    SIMULATION PARAMETER: Time constants are modeling assumptions, not physiology.
    """
    tau_config = config["tau"]
    n = circuit.n_neurons
    tau = np.ones(n, dtype=np.float64) * tau_config.get("default", 10.0)

    for pop_name, tau_val in tau_config.items():
        if pop_name == "default":
            continue
        indices = circuit.get_population_indices(pop_name)
        for idx in indices:
            tau[idx] = tau_val

    return tau


def build_bias_vector(circuit: loader.CircuitData, config: dict) -> np.ndarray:
    """Build per-neuron bias vector from config.

    SIMULATION PARAMETER: Biases are modeling assumptions, not physiology.
    """
    bias_config = config.get("bias", {})
    n = circuit.n_neurons
    b = np.ones(n, dtype=np.float64) * bias_config.get("default", 0.0)

    for pop_name, bias_val in bias_config.items():
        if pop_name == "default":
            continue
        indices = circuit.get_population_indices(pop_name)
        for idx in indices:
            b[idx] = bias_val

    return b


def run_simulation(
    circuit: loader.CircuitData,
    config: dict,
    u_func: Callable[[float, int], np.ndarray],
    x0: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, readouts.SimulationReadout]:
    """Run a complete simulation with the given circuit and inputs.

    Args:
        circuit: Loaded and validated circuit data.
        config: Simulation configuration dictionary.
        u_func: Input function u(t, n_neurons) -> np.ndarray.
        x0: Initial state. None = zeros.

    Returns:
        (times, states, readout) tuple.
    """
    # Build signed weight matrix
    sign_map = config["sign_map"]
    W_signed = loader.build_signed_weight_matrix(circuit, sign_map)

    # Build parameter vectors
    tau = build_tau_vector(circuit, config)
    b = build_bias_vector(circuit, config)
    gain = config["gain"]
    dt = config["dt"]
    duration = config["duration"]
    clip_max = config.get("clip_max", None)
    noise_std = config.get("noise_std", 0.0)
    seed = config.get("seed", None)

    # Scale input
    input_scale = config.get("input_scale", 1.0)
    if input_scale != 1.0:
        original_u_func = u_func
        def scaled_u_func(t: float, n: int) -> np.ndarray:
            return input_scale * original_u_func(t, n)
        u_func = scaled_u_func

    # RNG for noise (deterministic)
    rng = None
    if noise_std > 0.0:
        if seed is None:
            raise ValueError("noise_std > 0 but no seed specified — non-deterministic!")
        rng = np.random.default_rng(seed)

    # Run simulation
    times, states = dynamics.simulate(
        W_signed=W_signed,
        tau=tau,
        gain=gain,
        dt=dt,
        duration=duration,
        u_func=u_func,
        b=b,
        x0=x0,
        clip_max=clip_max,
        noise_std=noise_std,
        rng=rng,
    )

    # Extract readouts
    sim_readout = readouts.extract_readouts(circuit, times, states, dt)

    return times, states, sim_readout
