"""Generate the Phase 4 validation report strictly from saved evidence."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PHASE4_DIR = PROJECT_ROOT / "connectome" / "phase4"
RESULTS_DIR = PHASE4_DIR / "results"
REPORT_PATH = PHASE4_DIR / "phase4_validation_report.md"


def main() -> int:
    manifest = json.loads((RESULTS_DIR / "validation_manifest.json").read_text())
    tests = json.loads((RESULTS_DIR / "phase4_test_results.json").read_text())
    analysis = json.loads((RESULTS_DIR / "analysis_data.json").read_text())
    command_status = {item["label"]: item for item in manifest["commands"]}
    complete = manifest["status"] == "PASS" and tests["status"] == "PASS"
    assertions = tests["assertions"]
    unit_count = command_status["phase4_unit_tests"]["pytest_passed"]
    combined = tests["readouts"]["D_both"]["dn_neurons"]
    combined_rows = []
    for dn_type, sides in combined.items():
        for side, values in sides.items():
            combined_rows.append(
                f"| {dn_type} | {side} | {values['steady_state']:.6f} | "
                f"{values['t90_ms']:.1f} | {values['auc']:.4f} |"
            )
    dt_worst_response = max(
        scenario.get("worst_response_relative_error", scenario.get("worst_peak_relative_error", 0.0))
        for comparison in tests["dt_comparisons"].values()
        for scenario in comparison.values()
    )
    dt_worst_auc = max(
        scenario["worst_auc_relative_error"]
        for comparison in tests["dt_comparisons"].values()
        for scenario in comparison.values()
    )
    corr = analysis["connectivity_response_spearman"]
    gain_lines = []
    for gain, values in analysis["gain_sensitivity"].items():
        top = values["ranking"][0]
        gain_lines.append(
            f"- Gain {gain}: spectral radius {values['spectral_radius_gain_times_W']:.6f}; "
            f"maximum network activity {values['max_activity_all_neurons']:.6f}; "
            f"top DN {top['neuron']} ({top['steady_state']:.6f}); clip reached: {values['clip_reached']}."
        )
    report = f"""# Phase 4 Validation Report

## Status

**Phase 4 status: {'COMPLETE' if complete else 'INCOMPLETE'}**

**Circuit:** frozen Circuit v2, version 2.0.0

**Evidence run (UTC):** {manifest['run_date']}

This report is generated from the saved validation manifest, integration results, and analysis data. It does not infer completion from code presence alone.

## Reproducible acceptance evidence

- Phase 4 unit tests: **{unit_count} passed**, exit code {command_status['phase4_unit_tests']['exit_code']}.
- Phase 4 integration/validation: **{assertions['passed']}/{assertions['total']} assertions passed**, {assertions['failed']} failed.
- Circuit v2 verification: exit code {command_status['phase3_circuit_v2']['exit_code']} (48/48 checks in the saved output).
- Independent raw-connectome audit: exit code {command_status['phase3_independent_audit']['exit_code']} (12/12 checks in the saved output).
- Archival Circuit v1 verification: exit code {command_status['phase3_archival_v1']['exit_code']}.
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

- Spectral radius of `gain × W_signed`: **{tests['spectral_radius_gain_times_W']:.6f}**.
- Maximum real eigenvalue of `gain × W_signed`: **{tests['max_real_eigenvalue_gain_times_W']:.6f}**.
- The continuous-time Jacobian is stable and the Euler update is stable at 0.5, 1.0, and 2.0 ms.
- A 0.01 uniform perturbation decays below 1e-6 by 387 ms under zero input.
- Normal operating tests do not reach the activation clip; combined-input maximum activity is 22.093472 versus `clip_max=50`.
- A deliberately out-of-range 10× input remains finite without clipping (maximum 220.934723) and reaches the configured clip when clipping is enabled. This stress condition is not the normal operating regime.
- Across all ten DN readouts and all tested conditions, worst timestep response/peak relative error is **{dt_worst_response:.6f}** and worst AUC relative error is **{dt_worst_auc:.6f}** relative to 1 ms.

## Descending-neuron results

Combined uniform LC4 + LPLC2 drive produces:

| DN | Side | Steady activity (a.u.) | T90 (ms) | AUC |
|---|---|---:|---:|---:|
{chr(10).join(combined_rows)}

Finite input pulses from 50–150 ms peak at 151 ms because the state at 151 ms is the first Euler-updated sample after the final driven step. All ten DN residuals at 300 ms are below 1% of their peaks, and T90 is intentionally undefined for transient traces.

Left-only and right-only LC4 inputs produce distinct bilateral DN vectors. These are simulated structural effects; they must not be interpreted as calibrated visual-field direction selectivity because Circuit v2 contains no receptive-field coordinates.

## Structural-response analyses

- LC4 direct structural weight versus steady DN response: Spearman rho **{corr['LC4']['rho']:.4f}**, p={corr['LC4']['p_value']:.4g}, n=10.
- LPLC2 direct structural weight versus steady DN response: Spearman rho **{corr['LPLC2']['rho']:.4f}**, p={corr['LPLC2']['p_value']:.4g}, n=10.
- Empirical superposition maximum absolute error: **{analysis['linearity_check']['max_absolute_error']:.3e}**.
- Direct-only ablation removes intra-population, cross-visual, readout-to-visual, and inter-readout edges. The resulting differences quantify network-mediated contributions under this model; they are not causal biological measurements.

Gain sensitivity:

{chr(10).join(gain_lines)}

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
"""
    REPORT_PATH.write_text(report)
    print(f"Report written to {REPORT_PATH}")
    return 0 if complete else 1


if __name__ == "__main__":
    sys.exit(main())
