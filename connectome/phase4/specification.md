# Phase 4 Specification

## 1. Overview
This specification details the mathematical model and software architecture implemented in Phase 4 for simulating `circuit_v2`.

## 2. Mathematical Model
The dynamics follow a deterministic rate model.
**BIOLOGICAL FACT**: The circuit topology and synaptic weight ratios are derived directly from the MaleCNS v1.0 connectome.
**MODEL ASSUMPTION**: The dynamics are approximated by a continuous-time rate model.

Equation:
$$ \tau_i \frac{dx_i}{dt} = -x_i + \phi\left( \text{gain} \cdot \sum_j W_{\text{signed}}[i,j] x_j + b_i + u_i \right) $$

**SIMULATION PARAMETER**:
- $\tau_i$: Membrane time constant, set uniformly to $10 \text{ ms}$ across all populations.
- $\text{gain}$: Global synaptic scaling factor, set to $0.5$. Stability is
  verified from the full continuous-time Jacobian and explicit-Euler update
  operators; the recurrent spectral radius is $0.695832$ at this gain.
- $\phi$: ReLU function, optionally clipped to prevent extreme numerical overflow.
- $dt$: Integration time step for explicit Euler, default $1.0 \text{ ms}$.

## 3. Software Architecture
The `connectome/scripts/phase4/` package contains:
- `loader.py`: Ingests Circuit v2 CSV artifacts, constructs the $W[\text{post}, \text{pre}]$ matrix, and strictly validates all 321 neurons, 11,557 edges, and metadata against the frozen contract.
- `dynamics.py`: Implements the explicit Euler integration of the model equations.
- `inputs.py`: Provides input generation functions strictly addressing `bodyId`, limited to `LC4` and `LPLC2` for test driving.
- `readouts.py`: Extracts state histories for the primary (`DNp01`) and secondary (`DNp04`, `DNp02`, `DNp11`, `DNp06`) descending neurons.
- `simulator.py`: Orchestrates loading, initialization, step iteration, and readout generation.
- `validation.py`: Verifies continuous and discrete numerical stability,
  bitwise determinism, file immutability (via SHA-256), saturation behavior,
  and correct sign-map application.
- `validate_phase4.py`: Runs the complete acceptance pipeline and records the
  exact commands, exit codes, captured output hashes, and environment evidence.

## 4. Input-Output Contract
**Input:** Time-varying or static dictionary `{bodyId: drive_level}` restricted to visual projection neurons.
**Output:** Time series arrays for the full network state and summary metrics
(mean, maximum, peak time, terminal/steady activity, AUC, sustained-response
T90, and left-right differences) for target DNs. T90 is not defined for silent
or transient traces.

## 5. Limitations
**MODEL ASSUMPTION**: Spatial (retinotopic) organization is not available in the underlying dataset and thus not simulated.
**MODEL ASSUMPTION**: No spiking dynamics.
**MODEL ASSUMPTION**: All synapses are modeled as excitatory (+1) due to the underlying classifier predicting 100% cholinergic transmission.

Absolute rates, response magnitudes, and timing are not calibrated to fly
electrophysiology. The current non-negative, unsaturated tests operate in an
effectively linear regime; this is not a claim that the biological circuit is
linear.
