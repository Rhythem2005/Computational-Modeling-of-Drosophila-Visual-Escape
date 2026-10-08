# Phase 4: Deterministic Rate-Model Simulator for Circuit v2

This directory contains the Phase 4 biophysical simulation and behavioral modeling environment for the frozen `circuit_v2`.

## What this is
A deterministic rate-model simulator to compute network dynamics of the *Drosophila* visual escape circuit based *strictly* on the frozen Phase 3 connectome.

## What this is NOT
- NOT a visual field / retinotopy model (OpenCV/video are out of scope).
- NOT an optimization or machine learning project (no weight fitting).
- NOT a behavioral mapping (only neural readouts are produced).
- NOT stochastic (no random noise unless explicitly seeded for testing).

## Model Equation (SIMULATION PARAMETER)
The core dynamics are governed by a leaky integrate-and-fire rate model:

$$ \tau_i \frac{dx_i}{dt} = -x_i + \phi\left( \text{gain} \cdot \sum_j W_{\text{signed}}[i,j] x_j + b_i + u_i \right) $$

where:
- $\phi(z) = \max(0, z)$ is a ReLU activation function.
- $W_{\text{signed}}[i,j]$ is the normalized weight matrix W[post, pre] multiplied by the synaptic sign.
- $\tau_i = 10 \text{ ms}$ default time constant for all neurons.
- $\text{gain} = 0.5$, chosen *a priori* by spectral radius stability ($\rho = 0.696 < 1.0$) rather than by tuning to DN output.

## Sign Assumption (MODEL ASSUMPTION)
The synaptic polarity is assigned based strictly on the predicted neurotransmitter metadata.
- Acetylcholine $\rightarrow +1$ (Excitatory)
- GABA $\rightarrow -1$ (Inhibitory)
- Glutamate $\rightarrow -1$ (Inhibitory)

> [!NOTE]
> All 321 neurons in Circuit v2 are predicted cholinergic, meaning all synaptic signs are $+1$ in this simulation. This is a modeling assumption, not an experimentally established biological fact.

## Interface
The inputs to the system are provided as a dictionary mapping `{bodyId: drive}`. This allows Phase 5/6 to inject arbitrary visual encodings without touching the dynamics core.
Test stimulations in Phase 4 are restricted strictly to visual inputs (`LC4` and `LPLC2`).
State is maintained strictly by `bodyId` (no merging of left/right).

## Readouts
Readouts are extracted for the DNs:
- **Primary:** `DNp01`
- **Secondary:** `DNp04`, `DNp02`, `DNp11`, `DNp06`
Metrics reported per neuron, hemisphere, and population: mean, max, peak time, AUC, and Left-Right difference.

## Tests & Validation
The environment includes comprehensive unit tests and rigorous integration tests (Tests A-F). All stability criteria and validation checks are defined a priori.
The simulation validates the exact integers of the loaded frozen circuit against the Phase 3 contract and ensures no mutations are possible.

## How to Run
```bash
# Run the complete test suite and validations
./venv/bin/python connectome/scripts/phase4/run_phase4_tests.py

# Generate diagnostic plots
./venv/bin/python connectome/scripts/phase4/generate_plots.py
```
