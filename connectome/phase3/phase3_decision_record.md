# Phase 3: Decision & Epistemic Record

**Phase:** Phase 3
**Status:** COMPLETE & INDEPENDENTLY VERIFIED
**Date:** 2026-09-22
**Dataset:** Drosophila MaleCNS v1.0 (`male-cns:v1.0`)

---

## 1. Epistemic Framework

Every fact, parameter, and assumption in Phase 3 is explicitly partitioned across five epistemic layers:

- **Layer 1: Connectome-Derived Facts (MaleCNS v1.0 Data):** Directly measured synapse counts, cell reconstructions, soma coordinates, and body annotations.
- **Layer 2: Derived Quantitative Metrics:** Reproducibly computed quantities (e.g. `visual_share`, threshold survivability at $w_{\min} \in \{1, 3, 10\}$, two-step path scores).
- **Layer 3: Biological Literature Evidence:** Published experimental findings (electrophysiology, optogenetics, behavioral tracking) with verified citations.
- **Layer 4: Computational Modeling Assumptions:** Deliberate modeling simplifications (e.g., feedforward scope, unsigned weights, absence of fabricated retinotopy).
- **Layer 5: Frozen Circuit Parameters:** Exact node sets, edge sets, thresholds, normalization divisors, and schema definitions.

---

## 2. Layer 1: Connectome Facts (MaleCNS v1.0)

| Fact ID | Fact Description | Source Dataset | Verification Check |
|---|---|---|---|
| F-01 | LC4 population consists of exactly 126 traced neurons (71L, 55R). | `body-annotations` (`type == 'LC4'`) | `verify_circuit_v2.py` Check 6 |
| F-02 | LPLC2 population consists of exactly 185 traced neurons (94L, 91R). | `body-annotations` (`type == 'LPLC2'`) | `verify_circuit_v2.py` Check 6 |
| F-03 | DNp01 has exactly 2 traced neurons (10010 L, 10001 R). | `body-annotations` (`type == 'DNp01'`) | `verify_circuit_v2.py` Check 6 |
| F-04 | DNp04 has exactly 2 traced neurons (531898 L, 11137 R). | `body-annotations` (`type == 'DNp04'`) | `verify_circuit_v2.py` Check 6 |
| F-05 | DNp06 has exactly 2 traced neurons (10228 L, 10584 R). | `body-annotations` (`type == 'DNp06'`) | `verify_circuit_v2.py` Check 6 |
| F-06 | DNp02 has exactly 2 traced neurons (10197 L, 10117 R). | `body-annotations` (`type == 'DNp02'`) | `verify_circuit_v2.py` Check 6 |
| F-07 | DNp11 has exactly 2 traced neurons (10259 L, 10106 R). | `body-annotations` (`type == 'DNp11'`) | `verify_circuit_v2.py` Check 6 |
| F-08 | Exactly 11,557 directed edges exist among the 321 Circuit v2 neurons at $w \ge 3$. | `connectome-weights` | `verify_circuit_v2.py` Check 7 |
| F-09 | All 321 neurons in Circuit v2 are predicted cholinergic (acetylcholine) with classifier confidence 0.84–0.99. | `body-neurotransmitters` | `verify_circuit_v2.py` Check 11 |
| F-10 | True optic lobe column metadata (`assignedOlHex1`, `assignedOlHex2`) is NULL for all 311 visual projection neurons. | `body-annotations` | Audit in Phase 2 & Phase 3 |

---

## 3. Layer 2: Derived Quantitative Metrics

| Metric ID | Quantity | Derivation Formula / Method | Value in Circuit v2 |
|---|---|---|---|
| D-01 | **Visual Input Share ($w_1$)** | $\frac{\text{LC4\_weight} + \text{LPLC2\_weight}}{\text{total\_incoming\_weight}}$ | DNp04: 68.2%; DNp01: 25.8%; DNp02: 23.0%; DNp11: 15.4%; DNp06: 6.6% |
| D-02 | **Threshold Weight Retention ($w_{10} / w_1$)** | $\frac{\text{visual\_weight}(w_{\min}=10)}{\text{visual\_weight}(w_{\min}=1)}$ | DNp01: 98.6%; DNp02: 98.1%; DNp04: 97.8%; DNp11: 93.5%; DNp06: 65.4% |
| D-03 | **Max Synaptic Weight** | $\max_{(u,v)} W_{uv}$ across circuit pairs | 172 (intra-LPLC2 connection) |
| D-04 | **Linear Max-Normalization** | $W_{\text{norm}} = \frac{W}{172}$ | Range $[0.0174, 1.0000]$ for $w \ge 3$ |
| D-05 | **Dual Visual Convergence Ratio** | $\text{LC4\_weight} : \text{LPLC2\_weight}$ ($w_3$) | DNp01: 57:43; DNp04: 77:23; DNp06: 40:60; DNp02: 100:0; DNp11: 99:1 |

---

## 4. Layer 3: Biological Evidence Assessment

| Population | Verified Physiological Function | In Vivo Evidence Type | Escape Role | Key Reference |
|---|---|---|---|---|
| **LC4** | Looming angular expansion velocity detector | In vivo 2-photon imaging, patch clamp | Velocity trigger | von Reyn et al. (2014; 2017) |
| **LPLC2** | Looming angular size detector via radial motion opponency | In vivo 2-photon imaging, optogenetics | Size trigger | Klapoetke et al. (2017) |
| **DNp01** | Giant Fiber; monosynaptic drive to motor giant (TTMn) & PSI | Electrophysiology, optogenetics, kinematics | Unsteered emergency jump | Tanouye & Wyman (1980); von Reyn et al. (2014) |
| **DNp04** | Descending neuron spanning entire LC4 glomerulus; takeoff steering | Optogenetics, connectomics, behavior | Takeoff steering | Peek (2018); Dombrovski et al. (2023) |
| **DNp06** | Descending neuron projecting to dorsal VNC wing motor center | Tethered-flight optogenetics, wing kinematics | Evasive flight turns | Kim et al. (2023); Namiki et al. (2018) |
| **DNp02** | Ventral LC4 glomerulus descending neuron; synergistic takeoff partner of DNp04 | Optogenetics, connectomics, kinematics | Backward takeoff steering | Peek (2018); Dombrovski et al. (2023) |
| **DNp11** | LC4 glomerulus descending neuron; forward jump driver | Optogenetics, behavioral kinematics | Forward takeoff steering | Peek (2018); Dombrovski et al. (2023) |

---

## 5. Layer 4: Computational Modeling Assumptions

| Assumption | Epistemic Justification | Alternative Rejected | Impact on Phase 4 Simulation |
|---|---|---|---|
| **Feedforward Purity (No Interneurons)** | Intermediate interneurons (PVLP010, LHAD1g1, etc.) lack single-cell functional calibration. | Including 4,540 intermediate interneurons with unmeasured parameters. | Phase 4 focuses on monosynaptic sensorimotor integration without uncalibrated latent states. |
| **Unsigned Synaptic Weights** | Connectome data reports structural synapse counts, not conductances or sign. | Arbitrarily baking $+1$ into weights. | Phase 4 explicitly applies synaptic sign (+1 for acetylcholine) during conductance conversion. |
| **No Fabricated Retinotopy** | MaleCNS v1.0 has NULL retinotopic column metadata for LC4/LPLC2. Soma locations do NOT represent receptive fields. | Fabricating visual angles from soma centroids. | Phase 4 must use an explicitly documented stimulus mapping model rather than claiming true retinotopy. |
| **Threshold $w_{\min}=3$** | Prunes noise-level single/double synapses while retaining >98% of total visual weight onto readouts. | $w_{\min}=1$ (excessive noise) or $w_{\min}=10$ (dilutes DNp06). | Reduces edge count from 21,611 to 11,557 while preserving essential circuit topology. |
| **Max Normalization ($\div 172$)** | Preserves linear dynamic range and exact integer ratios between pathways. | Log-transform or z-scoring. | Normalized weights remain in $[0, 1]$ for straightforward scaling. |

---

## 6. Layer 5: Frozen Circuit Decision

### Scope Decision: Scope B Formally Frozen as Circuit v2
- **Archival Baseline:** Circuit v1 remains frozen and verified in `connectome/phase3/circuit_v1_*`.
- **Refrozen Circuit:** Circuit v2 is frozen in `connectome/phase3/circuit_v2_*`.
- **Rationale:** While Circuit v1 captured the direct dual-convergence baseline, Phase 2 biological literature evidence proved that DNp04 acts in synergy with DNp02 during backward takeoff, and DNp11 directs forward takeoff. Freezing Circuit v2 provides Phase 4 with an expanded directional escape steering circuit without adding uncalibrated interneuron parameters.

---

## 7. Status of Unresolved Decisions

1. **Takeoff Steering Expansion:** Resolved by freezing Circuit v2 ({DNp01, DNp04, DNp06, DNp02, DNp11}).
2. **Interneuron Inclusion:** Formally deferred to Scope C (future multi-stage work).
3. **DNp06 Status:** Confirmed as an in-flight evasive steering readout, with documented recognition of its lower connectomic visual share (~6.5%).
