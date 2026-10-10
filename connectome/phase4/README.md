# Phase 4: Deterministic Rate-Model Simulator for Circuit v2

This directory contains the completed Phase 4 deterministic rate-model simulator for frozen `circuit_v2`.

## What this is
A deterministic rate-model simulator to compute network dynamics of the *Drosophila* visual escape circuit based *strictly* on the frozen Phase 3 connectome.

## What this is NOT
- NOT a visual field / retinotopy model (OpenCV/video are out of scope).
- NOT an optimization or machine learning project (no weight fitting).
- NOT a behavioral mapping (only neural readouts are produced).
- NOT stochastic (no random noise unless explicitly seeded for testing).

## Model Equation (SIMULATION PARAMETER)
The core dynamics are governed by a continuous-valued leaky rate model (not a spiking leaky integrate-and-fire model):

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
Metrics reported per neuron, hemisphere, and population include mean, maximum,
peak time, terminal/steady activity, AUC, sustained-response T90, and left-right
difference. T90 is undefined (`null` in JSON) for silent or transient traces.

## Tests & Validation
The environment includes unit, integration, stability, timestep-sensitivity,
pulse, stress, determinism, and immutability checks. The general stability test
uses the continuous-time Jacobian `diag(1/tau) @ (-I + gain*W_signed)` and the
explicit-Euler update operator at each tested timestep.

The authoritative evidence is in `results/validation_manifest.json`,
`results/phase4_test_results.json`, `results/analysis_data.json`, and
`phase4_validation_report.md`.

## How to Run
```bash
# Run the complete acceptance pipeline (unit tests, Phase 3 invariant checks,
# integration validation, analysis, and plots)
./venv/bin/python connectome/scripts/phase4/validate_phase4.py

# Regenerate the evidence-derived report
./venv/bin/python connectome/scripts/phase4/generate_report.py

# Individual components remain runnable
./venv/bin/python connectome/scripts/phase4/run_phase4_tests.py
./venv/bin/python connectome/scripts/phase4/analyze_phase4.py
./venv/bin/python connectome/scripts/phase4/generate_plots.py
```
