"""Rate-model dynamics core for Phase 4 simulation.

MODEL EQUATION (SIMULATION PARAMETER, NOT MEASURED PHYSIOLOGY):
    tau_i * dx_i/dt = -x_i + phi(sum_j W_signed[i,j] * x_j + b_i + u_i)

phi(z) = max(0, z)  with optional configurable clip
Integration: Explicit Euler, default dt = 1 ms

All parameters are simulation parameters, not measured physiology.
"""

from __future__ import annotations

import numpy as np


def phi_relu(z: np.ndarray, clip_max: float | None = None) -> np.ndarray:
    """Activation function: ReLU with optional clip.

    MODEL ASSUMPTION: ReLU chosen as simplest monotonic non-negative transfer function.
    clip_max prevents runaway activity but is NOT a physiological saturation level.

    Args:
        z: Input array.
        clip_max: Optional upper bound for clipping. None = no clip.

    Returns:
        Element-wise max(0, z), optionally clipped at clip_max.
    """
    out = np.maximum(0.0, z)
    if clip_max is not None:
        np.clip(out, 0.0, clip_max, out=out)
    return out


def euler_step(
    x: np.ndarray,
    W_signed: np.ndarray,
    b: np.ndarray,
    u: np.ndarray,
    tau: np.ndarray,
    gain: float,
    dt: float,
    clip_max: float | None = None,
) -> np.ndarray:
    """Single explicit Euler integration step.

    SIMULATION PARAMETER: tau, gain, dt are modeling parameters, not physiology.

    tau_i * dx_i/dt = -x_i + phi(gain * sum_j W_signed[i,j] * x_j + b_i + u_i)

    x_{t+1} = x_t + (dt / tau_i) * (-x_t + phi(gain * W @ x_t + b + u))

    Args:
        x: State vector [n_neurons].
        W_signed: Signed weight matrix W[post, pre] [n_neurons x n_neurons].
        b: Bias vector [n_neurons].
        u: External input vector [n_neurons].
        tau: Time constant vector [n_neurons] (ms).
        gain: Global gain factor (scalar).
        dt: Time step (ms).
        clip_max: Optional activation clip.

    Returns:
        Updated state vector x_{t+1}.
    """
    # W @ x computes sum_j W[i,j] * x[j] for each i (postsynaptic)
    drive = gain * (W_signed @ x) + b + u
    activation = phi_relu(drive, clip_max)
    dx = (dt / tau) * (-x + activation)
    return x + dx


def simulate(
    W_signed: np.ndarray,
    tau: np.ndarray,
    gain: float,
    dt: float,
    duration: float,
    u_func,
    b: np.ndarray | None = None,
    x0: np.ndarray | None = None,
    clip_max: float | None = None,
    noise_std: float = 0.0,
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Run rate-model simulation.

    Args:
        W_signed: Signed weight matrix [n x n], W[post, pre].
        tau: Time constant vector [n].
        gain: Global gain scalar.
        dt: Time step (ms).
        duration: Total simulation time (ms).
        u_func: Callable(t, n_neurons) -> np.ndarray returning input at time t.
                This is the interface for Phase 5/6 to inject inputs without
                touching the dynamics core.
        b: Bias vector [n]. Defaults to zeros.
        x0: Initial state [n]. Defaults to zeros.
        clip_max: Optional activation clip.
        noise_std: Standard deviation of additive noise. 0 = deterministic.
        rng: NumPy random generator for reproducibility. Required if noise_std > 0.

    Returns:
        (times, states) where:
            times: 1D array of time points [n_steps + 1].
            states: 2D array [n_steps + 1, n_neurons] of state trajectories.
    """
    n = W_signed.shape[0]
    n_steps = int(duration / dt)

    if b is None:
        b = np.zeros(n, dtype=np.float64)
    if x0 is None:
        x0 = np.zeros(n, dtype=np.float64)

    times = np.arange(0, n_steps + 1, dtype=np.float64) * dt
    states = np.zeros((n_steps + 1, n), dtype=np.float64)
    states[0] = x0.copy()

    for step in range(n_steps):
        t = times[step]
        u = u_func(t, n)

        if noise_std > 0.0 and rng is not None:
            noise = rng.normal(0.0, noise_std, size=n)
            u = u + noise

        states[step + 1] = euler_step(
            x=states[step],
            W_signed=W_signed,
            b=b,
            u=u,
            tau=tau,
            gain=gain,
            dt=dt,
            clip_max=clip_max,
        )

    return times, states


def compute_spectral_radius(W_signed: np.ndarray, gain: float) -> float:
    """Compute spectral radius (max absolute eigenvalue) of gain * W_signed.

    SIMULATION RESULT: Used to choose gain for numerical stability.
    This is a linear stability analysis, not a biological prediction.

    Args:
        W_signed: Signed weight matrix.
        gain: Global gain factor.

    Returns:
        Spectral radius of gain * W_signed.
    """
    eigenvalues = np.linalg.eigvals(gain * W_signed)
    return float(np.max(np.abs(eigenvalues)))


def compute_max_real_eigenvalue(W_signed: np.ndarray, gain: float) -> float:
    """Compute maximum real part of eigenvalues of gain * W_signed.

    SIMULATION RESULT: For stability of the linearized system, need max Re(lambda) < 1
    (for Euler with specific tau/dt).

    Args:
        W_signed: Signed weight matrix.
        gain: Global gain factor.

    Returns:
        Maximum real part of eigenvalues.
    """
    eigenvalues = np.linalg.eigvals(gain * W_signed)
    return float(np.max(np.real(eigenvalues)))
