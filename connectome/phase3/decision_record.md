# Circuit v1 — Decision and Assumption Record

This document separates every component of Circuit v1 into its epistemic category, from connectome-derived facts through computational assumptions to frozen parameters.

---

## Layer 1: Connectome-Derived Facts

These are direct observations from the MaleCNS v1.0 dataset. They are not decisions — they are data.

| Fact | Source | Verification |
|------|--------|-------------|
| LC4 has 126 neurons (63L + 63R) | body-annotations, type="LC4" | verify_circuit_v1.py check 6 |
| LPLC2 has 185 neurons (92L + 93R) | body-annotations, type="LPLC2" | verify_circuit_v1.py check 6 |
| DNp01 has 2 neurons (1L + 1R) | body-annotations, type="DNp01" | verify_circuit_v1.py check 6 |
| DNp04 has 2 neurons (1L + 1R) | body-annotations, type="DNp04" | verify_circuit_v1.py check 6 |
| DNp06 has 2 neurons (1L + 1R) | body-annotations, type="DNp06" | verify_circuit_v1.py check 6 |
| Neuron body IDs, types, sides | body-annotations feather | verify_circuit_v1.py checks 3–5 |
| All 11,286 directed edges with w ≥ 3 | connectome-weights feather | verify_circuit_v1.py check 7 (exact match) |
| All synaptic weights (unsigned counts) | connectome-weights feather | verify_circuit_v1.py check 7 |
| DNp01(L) body ID = 10010 | body-annotations | Verified against source |
| DNp01(R) body ID = 10001 | body-annotations | Verified against source |
| DNp04(L) body ID = 531898 | body-annotations | Verified against source |
| DNp04(R) body ID = 11137 | body-annotations | Verified against source |
| DNp06(L) body ID = 10228 | body-annotations | Verified against source |
| DNp06(R) body ID = 10584 | body-annotations | Verified against source |

---

## Layer 2: Derived Quantities

These are computed from Layer 1 facts using explicit, reproducible procedures. The computation is documented; the choice of procedure is a decision (Layer 4/5).

| Quantity | Derivation | Parameters |
|----------|-----------|------------|
| Aggregated edge weights | Sum of all synaptic connections for same (pre, post) pair | No parameters — deterministic |
| Thresholded edges | Remove edges with aggregated weight < w_min | w_min = 3 (Layer 5) |
| Normalized weights | `weight / max_weight` | max_weight = 172 (Layer 1 fact after thresholding) |
| Edge classifications | Assigned by pre/post neuron type | Deterministic from types |
| Total visual input per readout | Sum of weights from LC4/LPLC2 → DN | Derived from edges |

---

## Layer 3: Biological Evidence

Evidence supporting circuit component roles, from connectome analysis (not external experiments).

| Component | Evidence | Strength | Limitation |
|-----------|----------|----------|------------|
| **DNp01 = Giant Fiber** | Instance name "DNp01(GF)_L/R" in MaleCNS annotations; highest total visual input among named escape DNs (11,220 syn); receives input from both LC4 (6,362) and LPLC2 (4,858) | **Strong** — well-established in Drosophila neuroscience literature | Connectome structure only; functional role assumed from literature |
| **DNp04 as escape readout** | Highest total visual input of any descending neuron (14,985 syn); massive LC4 input (11,597); receives from both LC4 and LPLC2; identified as top candidate in Phase 1 discovery | **Strong** connectome evidence for visual input | No functional data from this connectome; role as "escape readout" is inferred from connectivity pattern |
| **DNp06 as escape readout** | Receives both LC4 (1,142) and LPLC2 (1,689) input; pre-selected in Phase 0 config; moderate visual input (2,831 syn) | **Moderate** — included in original project scope | Lower visual input than many other DNs (see excluded candidates) |
| **LC4 as looming sensor** | 126 neurons, all traced; looming-sensitive visual projection neuron type | **Strong** — well-established in literature | Functional role assumed from type annotation |
| **LPLC2 as looming sensor** | 185 neurons, all traced; lobula plate/lobula columnar type | **Strong** — well-established in literature | Functional role assumed from type annotation |
| **Acetylcholine prediction** | All 317 neurons predicted ACh with confidence 0.93–0.99; consensus NT also ACh | **Moderate** — classifier prediction, not experimental | MaleCNS v1.0 uses a trained classifier; predictions could be wrong |

---

## Layer 4: Computational Assumptions

These are engineering choices made to construct the frozen circuit. They are NOT biological facts.

| Assumption | Justification | Alternative | Impact |
|-----------|--------------|------------|--------|
| **w_min = 3** | Established in Phase 1 config.yaml; removes noise from very weak connections | w_min = 1 (all edges) or w_min = 10 (stringent) | w_min=3 removes 9,978 edges (47% of unique pairs). Main circuit pathways unaffected (visual→readout edges have mean weight 32.6) |
| **Max normalization** | Simple, reproducible, preserves relative strengths | Log transform, input normalization, no normalization | Linear rescaling; does not change relative ordering |
| **Unsigned weights** | Structural synapse counts do not encode sign; sign comes from neurotransmitter identity | Apply sign at freeze time | Phase 4 must handle sign assignment |
| **All edges are putatively excitatory** | All neurons predicted ACh (cholinergic); ACh is typically excitatory at nicotinic receptors in Drosophila | Some synapses could be inhibitory via muscarinic receptors | Phase 4 sign convention will determine effect |
| **No retinotopy** | MaleCNS v1.0 does not provide validated spatial mappings for LC4/LPLC2 | Fabricate mappings from ROI column IDs | Correct decision: do not fabricate absent data |
| **Complete subgraph extraction** | All edges among the 317 circuit neurons are included (not just feedforward) | Include only visual→readout edges | More complete; includes recurrent and feedback edges |

---

## Layer 5: Frozen Circuit v1 Parameters

These are the exact values shipped in the frozen circuit. They cannot be changed without creating Circuit v2.

| Parameter | Value | Set By |
|-----------|-------|--------|
| Circuit types | {LC4, LPLC2, DNp01, DNp04, DNp06} | Phase 0 (LC4, LPLC2, DNp01, DNp06) + Phase 1 discovery (DNp04) |
| w_min | 3 | Phase 1 config.yaml |
| Normalization method | max | Phase 1 config.yaml |
| Max weight (normalization divisor) | 172 | Derived from data |
| Total nodes | 317 | Derived from data |
| Total edges | 11,286 | Derived from data + w_min |
| Primary readout | DNp01 | Phase 2 decision |
| Secondary readouts | DNp04, DNp06 | Phase 2 decision |
| Retinotopy | NOT_AVAILABLE | MaleCNS v1.0 limitation |
| Neurotransmitter sign applied | No (unsigned weights) | Phase 3 decision |
| Weight convention | W[post, pre] | Phase 1 convention |

---

## Interneuron Inclusion Rule

> **Rule (established in Phase 3, based on Phase 2 findings):**
> No interneurons are included in Circuit v1.
>
> **Criterion:** Only neuron types explicitly selected in Phase 0 (LC4, LPLC2, DNp01, DNp06) and promoted via Phase 1 full-connectome discovery (DNp04) are included. Two-step pathway intermediates (e.g., PVLP122, SAD064, LPLC1, LPLC4) remain excluded candidates regardless of their path scores or convergence properties.
>
> **Justification:** Phase 2 did not promote any interneuron to circuit membership. The discovery identified 61,959 two-step pathways through hundreds of intermediate types, but none were validated for functional relevance. Including intermediates without functional evidence would dilute the circuit with unvalidated components.
>
> **Status:** This rule is frozen with Circuit v1. If future evidence supports interneuron inclusion, it must create Circuit v2.

---

## UNKNOWN / Null-Type Neurons

> **Rule:** No neurons with UNKNOWN or null type exist within Circuit v1.
>
> All 317 neurons have named types from the MaleCNS v1.0 annotations. The discovery analysis found UNKNOWN-type neurons as intermediate pathway targets, but none are included in the frozen circuit. This rule was applied uniformly — no case-by-case exceptions.

---

## Flagged Disagreements

### 1. DNp04 Not in Original Phase 0 Config

**Issue:** `config.yaml` lists neuron_types as [LC4, LPLC2, DNp01, DNp06] — DNp04 is absent. However, the Phase 1 full-connectome discovery (`phase1_discovery.py`) identified DNp04 as the #1 descending neuron by total visual input (14,995 syn across 2 neurons), exceeding DNp01 (11,224 syn). The user's Phase 3 instructions explicitly list "DNp04/DNp06 are recorded readouts," confirming DNp04's inclusion.

**Resolution:** DNp04 is included in Circuit v1 per user instruction. The original config.yaml was not updated because it documents the Phase 0 extraction pipeline, not the full circuit.

**Impact:** DNp04 edges were not in the original `processed_edges.csv` (Phase 0/1 neuPrint extraction). They were extracted from the source feather files in Phase 3, using the same w_min=3 threshold. All DNp04 edges are independently verified against source data (verify_circuit_v1.py check 7).

### 2. Discovery Totals vs Frozen Totals

**Issue:** Phase 1 discovery reported total visual input as: DNp01=11,224, DNp04=14,995, DNp06=2,871. Frozen circuit totals are: DNp01=11,220, DNp04=14,985, DNp06=2,831.

**Resolution:** The discrepancy is entirely explained by the w_min=3 threshold. Discovery used no threshold (all edges). Frozen circuit applies w_min=3, pruning a small number of very weak edges (1–2 synapse count). The ratios are 0.9996, 0.9993, and 0.9861 respectively — all within expected range.

### 3. Hemispheric Asymmetry in DNp01

**Issue:** DNp01 left receives 6,422 total visual synapses; DNp01 right receives 4,798 (ratio 1.34:1). This asymmetry exceeds the ~1.0:1 expected for bilaterally symmetric neurons.

**Resolution:** This is a connectome observation, not a Phase 3 decision. It is documented here for Phase 4 awareness. It could reflect biological variation, reconstruction quality differences, or genuine functional asymmetry. Phase 4 should not "correct" this without justification.
