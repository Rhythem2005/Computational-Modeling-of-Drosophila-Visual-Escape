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


def validate_config(config: dict[str, Any]) -> None:
    """Fail loudly when a simulation configuration is incomplete or invalid."""
    required = {"circuit", "dt", "duration", "gain", "phi", "tau", "sign_map"}
    missing = sorted(required - set(config))
    if missing:
        raise ValueError(f"Missing simulation config fields: {', '.join(missing)}")
    if not isinstance(config["circuit"], dict):
        raise ValueError("circuit configuration must be a mapping")
    if config["circuit"].get("version") != "2.0.0":
        raise ValueError("Phase 4 requires frozen Circuit v2 version 2.0.0")
    expected_files = {
        "nodes_file": "connectome/phase3/circuit_v2_nodes.csv",
        "edges_file": "connectome/phase3/circuit_v2_edges.csv",
    }
    for key, expected in expected_files.items():
        if config["circuit"].get(key) != expected:
            raise ValueError(f"circuit.{key} must reference {expected}")
    if config["phi"] != "relu":
        raise ValueError("Only the documented 'relu' activation is supported")
    for name in ("dt", "duration", "gain", "input_scale", "noise_std"):
        value = float(config.get(name, 0.0))
        if not np.isfinite(value):
            raise ValueError(f"{name} must be finite")
    if config["dt"] <= 0 or config["duration"] <= 0:
        raise ValueError("dt and duration must be positive")
    if config["gain"] < 0 or config.get("input_scale", 1.0) < 0:
        raise ValueError("gain and input_scale must be non-negative")
    if config.get("noise_std", 0.0) < 0:
        raise ValueError("noise_std must be non-negative")
    if config.get("noise_std", 0.0) > 0 and config.get("seed") is None:
        raise ValueError("noise_std > 0 requires an explicit seed")
    clip_max = config.get("clip_max")
    if clip_max is not None and (not np.isfinite(clip_max) or clip_max <= 0):
        raise ValueError("clip_max must be null or finite and positive")
    if "default" not in config["tau"]:
        raise ValueError("tau.default is required")
    for population, value in config["tau"].items():
        if not np.isfinite(value) or value <= 0:
            raise ValueError(f"tau.{population} must be finite and positive")
    for population, value in config.get("bias", {}).items():
        if not np.isfinite(value):
            raise ValueError(f"bias.{population} must be finite")
    valid_signs = {-1.0, 1.0}
    if not config["sign_map"]:
        raise ValueError("sign_map must not be empty")
    for transmitter, sign in config["sign_map"].items():
        if float(sign) not in valid_signs:
            raise ValueError(f"sign_map.{transmitter} must be -1 or +1")
    for name in ("response_floor", "convergence_step_tolerance",
                 "pulse_residual_fraction_tolerance", "dt_response_tolerance",
                 "dt_auc_tolerance"):
        if name in config and (not np.isfinite(config[name]) or config[name] < 0):
            raise ValueError(f"{name} must be finite and non-negative")
    dt_values = config.get("dt_values_ms", [config["dt"]])
    if not dt_values or any(not np.isfinite(value) or value <= 0 for value in dt_values):
        raise ValueError("dt_values_ms must contain finite positive values")
    gain_values = config.get("gain_sensitivity_values", [config["gain"]])
    if not gain_values or any(not np.isfinite(value) or value < 0 for value in gain_values):
        raise ValueError("gain_sensitivity_values must contain finite non-negative values")
    steps = config["duration"] / config["dt"]
    if not np.isclose(steps, round(steps), rtol=0.0, atol=1e-12):
        raise ValueError("duration must be an integer multiple of dt")


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load simulation configuration from YAML."""
    if config_path is None:
        config_path = CONFIG_PATH
    with open(config_path) as f:
        config = yaml.safe_load(f)
    if not isinstance(config, dict):
        raise ValueError("simulation configuration must be a YAML mapping")
    validate_config(config)
    return config


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
        if not indices:
            raise ValueError(f"tau configuration references unknown population '{pop_name}'")
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
        if not np.isfinite(bias_val):
            raise ValueError(f"bias.{pop_name} must be finite")
        indices = circuit.get_population_indices(pop_name)
        if not indices:
            raise ValueError(f"bias configuration references unknown population '{pop_name}'")
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
    validate_config(config)

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
