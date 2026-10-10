"""Input generation for Phase 4 simulation.

Provides input functions that Phase 5/6 can use without touching dynamics core.
Inputs are specified as {bodyId: drive_value} — static or time-varying.
Test stimulation is restricted to LC4/LPLC2 neurons only.
"""

from __future__ import annotations

from typing import Callable

import numpy as np

from . import loader


def _validate_side(side: str | None) -> None:
    if side not in (None, "left", "right"):
        raise ValueError("side must be None, 'left', or 'right'")


def _validate_drive(value: float, label: str) -> None:
    if not np.isscalar(value) or not np.isfinite(value):
        raise ValueError(f"drive for {label} must be a finite scalar")


def make_zero_input() -> Callable[[float, int], np.ndarray]:
    """Return a zero input function."""
    def u_func(t: float, n: int) -> np.ndarray:
        return np.zeros(n, dtype=np.float64)
    return u_func


def make_static_input(
    circuit: loader.CircuitData,
    drive_map: dict[int, float],
) -> Callable[[float, int], np.ndarray]:
    """Create a static (constant) input function from bodyId -> drive value.

    Args:
        circuit: Loaded circuit data.
        drive_map: {bodyId: drive_value}. Must be LC4/LPLC2 neurons only.

    Returns:
        Input function u(t, n) -> array.
    """
    # Validate: only LC4/LPLC2 neurons can receive test input
    for bid in drive_map:
        ntype = circuit.type_map.get(bid)
        if ntype not in ("LC4", "LPLC2"):
            raise ValueError(
                f"bodyId {bid} is type '{ntype}', not LC4/LPLC2. "
                "Test stimulation restricted to visual input neurons."
            )
        _validate_drive(drive_map[bid], f"bodyId {bid}")

    n = circuit.n_neurons
    u_vec = np.zeros(n, dtype=np.float64)
    for bid, val in drive_map.items():
        idx = circuit.id_to_idx[bid]
        u_vec[idx] = val

    def u_func(t: float, n: int) -> np.ndarray:
        return u_vec.copy()

    return u_func


def make_population_input(
    circuit: loader.CircuitData,
    populations: dict[str, float],
    side: str | None = None,
) -> Callable[[float, int], np.ndarray]:
    """Create a uniform input to all neurons of specified populations.

    Args:
        circuit: Loaded circuit data.
        populations: {neuron_type: drive_value}, e.g. {"LC4": 1.0, "LPLC2": 0.5}.
                     Types must be LC4 or LPLC2.
        side: Optional side filter ("left" or "right"). None = both.

    Returns:
        Input function u(t, n) -> array.
    """
    _validate_side(side)
    for pop_name in populations:
        if pop_name not in ("LC4", "LPLC2"):
            raise ValueError(f"Population '{pop_name}' not LC4/LPLC2.")
        _validate_drive(populations[pop_name], pop_name)

    n = circuit.n_neurons
    u_vec = np.zeros(n, dtype=np.float64)
    for pop_name, drive_val in populations.items():
        indices = circuit.get_population_indices(pop_name, side=side)
        for idx in indices:
            u_vec[idx] = drive_val

    def u_func(t: float, n: int) -> np.ndarray:
        return u_vec.copy()

    return u_func


def make_pulse_input(
    circuit: loader.CircuitData,
    populations: dict[str, float],
    onset: float,
    offset: float,
    side: str | None = None,
) -> Callable[[float, int], np.ndarray]:
    """Create a finite pulse input that is active only during [onset, offset).

    Args:
        circuit: Loaded circuit data.
        populations: {neuron_type: drive_value}.
        onset: Start time of pulse (ms).
        offset: End time of pulse (ms).
        side: Optional side filter.

    Returns:
        Input function u(t, n) -> array.
    """
    _validate_side(side)
    if not np.isfinite(onset) or not np.isfinite(offset) or onset < 0 or offset <= onset:
        raise ValueError("pulse onset/offset must be finite with 0 <= onset < offset")
    for pop_name in populations:
        if pop_name not in ("LC4", "LPLC2"):
            raise ValueError(f"Population '{pop_name}' not LC4/LPLC2.")
        _validate_drive(populations[pop_name], pop_name)

    n = circuit.n_neurons
    u_on = np.zeros(n, dtype=np.float64)
    for pop_name, drive_val in populations.items():
        indices = circuit.get_population_indices(pop_name, side=side)
        for idx in indices:
            u_on[idx] = drive_val

    u_off = np.zeros(n, dtype=np.float64)

    def u_func(t: float, n: int) -> np.ndarray:
        if onset <= t < offset:
            return u_on.copy()
        return u_off.copy()

    return u_func


def make_time_varying_input(
    circuit: loader.CircuitData,
    drive_schedule: Callable[[float], dict[int, float]],
) -> Callable[[float, int], np.ndarray]:
    """Create a time-varying input from a schedule function.

    This is the general interface for Phase 5/6 to inject arbitrary
    time-varying inputs without touching the dynamics core.

    Args:
        circuit: Loaded circuit data.
        drive_schedule: Function(t) -> {bodyId: drive_value} at time t.

    Returns:
        Input function u(t, n) -> array.
    """
    n = circuit.n_neurons

    def u_func(t: float, n: int) -> np.ndarray:
        u = np.zeros(n, dtype=np.float64)
        drive_map = drive_schedule(t)
        if not isinstance(drive_map, dict):
            raise ValueError("drive_schedule must return a bodyId-to-drive dictionary")
        for bid, val in drive_map.items():
            ntype = circuit.type_map.get(bid)
            if ntype not in ("LC4", "LPLC2"):
                raise ValueError(
                    f"bodyId {bid} is type '{ntype}', not LC4/LPLC2; "
                    "time-varying stimulation is restricted to visual input neurons"
                )
            _validate_drive(val, f"bodyId {bid}")
            u[circuit.id_to_idx[bid]] = val
        return u

    return u_func
