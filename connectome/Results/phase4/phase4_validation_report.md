# Phase 4 Validation Report

## Status

**Phase 4 status: COMPLETE**

**Circuit:** frozen Circuit v2, version 2.0.0

**Evidence run (UTC):** 2026-10-10T10:18:50.601491+00:00

This report is generated from the saved validation manifest, integration results, and analysis data. It does not infer completion from code presence alone.

## Reproducible acceptance evidence

- Phase 4 unit tests: **49 passed**, exit code 0.
- Phase 4 integration/validation: **159/159 assertions passed**, 0 failed.
- Circuit v2 verification: exit code 0 (48/48 checks in the saved output).
- Independent raw-connectome audit: exit code 0 (12/12 checks in the saved output).
- Archival Circuit v1 verification: exit code 0.
- Analysis and all five diagnostic plots regenerated successfully.
- All six frozen Phase 3 hashes were unchanged during integration validation.

Run the same pipeline with:

```bash
./venv/bin/python connectome/scripts/phase4/validate_phase4.py
./venv/bin/python connectome/scripts/phase4/generate_report.py
```

## Model and scientific interpretation

**Biological/connectome evidence:** neuron identities, sides, directed topology, structural synapse counts, and predicted neurotransmitter metadata come from the frozen MaleCNS v1.0 Circuit v2 artifacts.

**Modeling assumptions:** normalized structural weights are converted to effective rate-model coupling; predicted acetylcholine is assigned sign +1; predicted GABA and glutamate would be assigned -1; all time constants are 10 ms; global gain is 0.5; input scale is 0.4; dynamics use ReLU and explicit Euler integration.

All 321 selected neurons are predicted cholinergic. Consequently, signed and unsigned matrices are identical for this circuit. Under the tested non-negative, unsaturated inputs, the model operates as an effectively linear dynamical system. This is a property of the implemented assumptions, not evidence that the biological circuit is physiologically linear.

## Stability and numerical validation

- Spectral radius of `gain × W_signed`: **0.695832**.
- Maximum real eigenvalue of `gain × W_signed`: **0.695832**.
- The continuous-time Jacobian is stable and the Euler update is stable at 0.5, 1.0, and 2.0 ms.
- A 0.01 uniform perturbation decays below 1e-6 by 387 ms under zero input.
- Normal operating tests do not reach the activation clip; combined-input maximum activity is 22.093472 versus `clip_max=50`.
- A deliberately out-of-range 10× input remains finite without clipping (maximum 220.934723) and reaches the configured clip when clipping is enabled. This stress condition is not the normal operating regime.
- Across all ten DN readouts and all tested conditions, worst timestep response/peak relative error is **0.004613** and worst AUC relative error is **0.001129** relative to 1 ms.

## Descending-neuron results

Combined uniform LC4 + LPLC2 drive produces:

| DN | Side | Steady activity (a.u.) | T90 (ms) | AUC |
|---|---|---:|---:|---:|
| DNp01 | left | 20.860028 | 78.0 | 9628.3362 |
| DNp01 | right | 11.655237 | 64.0 | 5457.0823 |
| DNp04 | left | 22.093472 | 69.0 | 10297.1026 |
| DNp04 | right | 13.858413 | 60.0 | 6513.2290 |
| DNp02 | left | 6.216400 | 66.0 | 2903.0182 |
| DNp02 | right | 4.499059 | 59.0 | 2116.0556 |
| DNp11 | left | 4.758209 | 63.0 | 2229.9049 |
| DNp11 | right | 8.973548 | 80.0 | 4121.0106 |
| DNp06 | left | 5.960590 | 78.0 | 2749.5701 |
| DNp06 | right | 4.661113 | 68.0 | 2168.1386 |

Finite input pulses from 50–150 ms peak at 151 ms because the state at 151 ms is the first Euler-updated sample after the final driven step. All ten DN residuals at 300 ms are below 1% of their peaks, and T90 is intentionally undefined for transient traces.

Left-only and right-only LC4 inputs produce distinct bilateral DN vectors. These are simulated structural effects; they must not be interpreted as calibrated visual-field direction selectivity because Circuit v2 contains no receptive-field coordinates.

## Structural-response analyses

- LC4 direct structural weight versus steady DN response: Spearman rho **0.8545**, p=0.001637, n=10.
- LPLC2 direct structural weight versus steady DN response: Spearman rho **0.8651**, p=0.001227, n=10.
- Empirical superposition maximum absolute error: **7.105e-15**.
- Direct-only ablation removes intra-population, cross-visual, readout-to-visual, and inter-readout edges. The resulting differences quantify network-mediated contributions under this model; they are not causal biological measurements.

Gain sensitivity:

- Gain 0.3: spectral radius 0.417499; maximum network activity 8.784817; top DN DNp04_left (8.784817); clip reached: False.
- Gain 0.5: spectral radius 0.695832; maximum network activity 22.093472; top DN DNp04_left (22.093472); clip reached: False.
- Gain 0.6: spectral radius 0.834998; maximum network activity 41.415728; top DN DNp01_left (41.415728); clip reached: False.

## Completed engineering work

- Strict Circuit v2 schema, endpoint, normalization, neurotransmitter, and matrix validation.
- Explicit simulation/configuration/input validation with finite-value and shape checks.
- Correct general stability analysis using `A = diag(1/tau) × (-I + gain×W)`.
- Defined peak time, steady state, AUC, and sustained-response T90 semantics; transient and silent T90 values serialize as `null`.
- Bilateral DN readouts for DNp01, DNp04, DNp02, DNp11, and DNp06.
- Zero-input, sustained-input, hemisphere-specific, pulse, stress, determinism, clipping, and timestep-sensitivity validation.
- Correct gain-sensitivity implementation without configuration mutation.
- Machine-readable results, analysis, command manifest, captured outputs, plots, and this evidence-derived report.

## Limitations and unresolved scientific questions

- Structural synapse counts are not measured conductances, and predicted transmitter identity is not experimentally established functional sign.
- Rate dynamics, gain, time constants, input scale, ReLU, and clipping are modeling choices without electrophysiological calibration.
- All selected neurons are predicted excitatory, so inhibitory sign behavior is verified synthetically but not exercised by Circuit v2.
- The circuit omits many interneurons, other descending neurons, non-visual inputs, and motor circuitry.
- No retinotopy, calibrated fly visual angles, spiking, adaptation, synaptic delays, or biological noise are modeled.
- Absolute activity magnitudes and times are computational units under this model and must not be presented as measured fly physiology.
- Correlations use only ten DN readouts and are descriptive, not evidence of biological optimality or connectome superiority.
- Behavioral decoding, visual encoding, comparisons, and ablations beyond the Phase 4 structural decomposition belong to later phases and were not started here.

There are no unresolved Phase 4 software failures in the recorded acceptance run. The unresolved items above are scientific limitations that downstream work must preserve and test explicitly.
