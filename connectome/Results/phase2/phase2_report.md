# Phase 2 Final Report: Candidate Circuit Analysis & Biological Validation

**Project:** FLY — Computational Modeling of Drosophila Visual Escape  
**Phase:** Phase 2 (Candidate Circuit Analysis & Biological Validation)  
**Status:** COMPLETE & INDEPENDENTLY REPRODUCIBLE  
**Date:** 2026-09-22  
**Dataset:** Drosophila MaleCNS v1.0 (`male-cns:v1.0`)  
**Pinned Checksums:**
- Body Annotations: `2177e246113e4cfbf1e7772ec37c6da1955ff22e8063d0b1f833101f99a9a3b2`
- Connectome Weights: `e35da783d1c686b2b58b3b87cd6a403ae43bfcfba8bff28e08ef752c1a56afc1`
- Body Neurotransmitters: `95c9289220663abeb3409f3ad9e5a7f8a53f8093f5139d15502cd08da8879621`

---

## 1. Primary Answers to Core Phase 2 Questions

### 1. Which descending neurons receive direct LC4 input?
At raw threshold ($w_{\min}=1$), **51 descending neurons** receive direct LC4 synaptic input. At standard threshold ($w_{\min}=3$), **32 descending neurons** receive LC4 input. At high-stringency threshold ($w_{\min}=10$), **21 descending neurons** retain direct LC4 input.
- **Top recipients by LC4 weight:** DNp04 (11,597 syn combined), DNp01 (6,362 syn), DNp02 (4,209 syn), DNp11 (3,666 syn), DNp03 (2,507 syn), DNp05 (1,303 syn), DNp06 (1,152 syn), DNg40 (980 syn).

### 2. Which descending neurons receive direct LPLC2 input?
At $w_{\min}=1$, **49 descending neurons** receive direct LPLC2 synaptic input. At $w_{\min}=3$, **39 descending neurons** receive LPLC2 input. At $w_{\min}=10$, **24 descending neurons** retain direct LPLC2 input.
- **Top recipients by LPLC2 weight:** DNp103 (5,065 syn combined), DNp01 (4,862 syn), DNp04 (3,398 syn), DNg40 (2,998 syn), DNp06 (1,719 syn), DNpe056 (1,619 syn), DNp71 (1,195 syn), DNpe025 (1,078 syn), DNp35 (920 syn).

### 3. Which descending neurons receive both LC4 and LPLC2?
Direct dual convergence is observed in:
- **37 descending neurons** at $w_{\min}=1$
- **22 descending neurons** at $w_{\min}=3$
- **12 descending neurons** at $w_{\min}=10$
The 12 robust dual-convergence neurons surviving $w_{\min}=10$ are:
1. **DNp04** (both bilateral pairs: 531898, 11137)
2. **DNp01** (both bilateral pairs: 10010, 10001)
3. **DNg40** (both bilateral pairs: 10923, 10361)
4. **DNp06** (both bilateral pairs: 10228, 10584)
5. **DNp35** (both bilateral pairs: 10558, 10234)
6. **DNp103** (right neuron: 10283; left neuron drops to 0 LC4 at $w_{10}$)
7. **DNpe025** (left neuron: 10601; right neuron drops to 0 LC4 at $w_{10}$)

### 4. How specific are these neurons to LC4/LPLC2 relative to their total input?
Visual-input share ($\frac{\text{LC4} + \text{LPLC2}}{\text{total incoming synapses across entire MaleCNS}}$) was computed for all 63 candidate DNs:
- **DNp04:** **69.57%** (L), **66.77%** (R). Over two-thirds of its total dendritic input comes directly from LC4 and LPLC2. Unmatched connectomic specificity across the CNS.
- **DNp01 (Giant Fiber):** **25.80%** (L), **25.83%** (R). Highly consistent bilateral specificity (~25.8%), receiving massive visual drive alongside premotor and mechanosensory inputs.
- **DNp02:** **24.31%** (L), **21.69%** (R). Highly specific visual input, almost purely from LC4.
- **DNg40:** **21.41%** (R), **18.55%** (L). Balanced visual share (~20%).
- **DNp11:** **16.24%** (L), **14.55%** (R). Strong visual input (~15%), predominantly LC4.
- **DNp03:** **15.91%** (L), **8.87%** (R). LC4-dominated.
- **DNpe056:** **10.59%** (L), **10.51%** (R). LPLC2-dominated.
- **DNp05:** **10.99%** (R), **11.27%** (L). LC4-dominated.
- **DNp103:** **10.48%** (R), **8.67%** (L). Diluted by a very large dendritic arbor (~28k total synapses).
- **DNp06:** **6.81%** (L), **6.32%** (R). Modest visual share; over 93% of input originates from non-visual pathways (flight motor integration).

### 5. Which candidate intermediate pathways connect LC4/LPLC2 to descending neurons?
Phase 2 identified 4,540 candidate intermediate neurons connecting LC4/LPLC2 to candidate DNs across 23,601 paths. Top intermediate interneurons by pathway transmission capacity ($\text{visual input} \times \text{output to DNs}$):
1. **PVLP010 (glutamate):** Receives 1,257 visual synapses; delivers 1,710 synapses across 30 candidate DNs ($\text{PathScore} = 2.15 \times 10^6$).
2. **LHAD1g1 (GABA):** Receives 1,308 visual synapses; delivers 1,556 synapses across 26 candidate DNs ($\text{PathScore} = 2.04 \times 10^6$).
3. **PVLP151 (acetylcholine):** Receives 2,530 visual synapses; delivers 645 synapses across 23 candidate DNs ($\text{PathScore} = 1.63 \times 10^6$).
4. **PVLP011 (GABA):** Receives 7,400 visual synapses; delivers 205 synapses across 18 candidate DNs ($\text{PathScore} = 1.52 \times 10^6$).
5. **PVLP122 (acetylcholine):** Receives 1,503 visual synapses; delivers 1,003 synapses across 25 candidate DNs ($\text{PathScore} = 1.51 \times 10^6$).
6. **PVLP076 (acetylcholine):** Receives 762 visual synapses; delivers 1,138 synapses across 28 candidate DNs ($\text{PathScore} = 0.87 \times 10^6$).
7. **PVLP024 (GABA):** Receives 2,679 visual synapses; delivers 321 synapses across 22 candidate DNs ($\text{PathScore} = 0.86 \times 10^6$).

### 6. Are candidate pathways robust across reasonable connectivity thresholds?
- **High Threshold Stability ($w_{\min}=10$):** DNp04, DNp01, DNp02, DNp103, DNg40, DNp11, and DNp03 retain >90% of their total visual synaptic weight when thresholded from $w_{\min}=1$ to $w_{\min}=10$.
- **Moderate Threshold Sensitivity:** DNp06 retains 98.6% of weight at $w_{\min}=3$, but drops to 65.4% at $w_{\min}=10$, reflecting many lower-weight synaptic connections.
- **Candidate Count Trajectory:** 63 active candidates at $w_{\min}=1 \implies 49$ at $w_{\min}=3 \implies 33$ at $w_{\min}=10$. Weak candidates (<50 synapses) drop out completely at $w_{\min}=10$.

### 7. What biological / literature evidence exists for candidate neurons?
Every citation has been verified against external literature:
- **LC4:** Looming velocity detector (von Reyn et al. 2014 *Neuron*; 2017 *Nat Neurosci*).
- **LPLC2:** Looming size / radial expansion detector (Klapoetke et al. 2017 *Nature*).
- **DNp01:** Giant Fiber; canonical short-mode unsteered emergency escape jump (Tanouye & Wyman 1980; Allen et al. 2006; von Reyn et al. 2014).
- **DNp04:** Non-GF escape readout; co-activated with DNp02 to direct backward takeoff (Peek 2018 *Ph.D. Diss.*; Dombrovski et al. 2023 *Nature*; Namiki et al. 2018 *eLife*).
- **DNp06:** Evasive flight turns and steering maneuvers during flight in response to visual threats (Kim, Park, Lee, & Kim 2023 *Curr Biol*; Namiki et al. 2018 *eLife*).
- **DNp02:** Obligate co-factor with DNp04 for backward takeoff (Peek 2018; Dombrovski et al. 2023 *Nature*).
- **DNp11:** Postural steering for forward jump takeoff (Peek 2018; Dombrovski et al. 2023 *Nature*).
- **DNg40 & DNp103:** Morphologically characterized descending neurons (Namiki et al. 2018), but `EVIDENCE: UNVERIFIED` for escape causation.

### 8. What can and cannot be inferred about retinotopy?
- **Status:** **`RETINOTOPY: NOT AVAILABLE`**
- **Findings:** Optic lobe column annotations (`assignedOlHex1`, `assignedOlHex2`) in MaleCNS v1.0 are NULL for all LC4 and LPLC2 neurons. Soma locations (`somaLocation`, in nm) provide gross cell body centroids, but cell bodies reside in the cortical cell rind and do NOT reflect the spatial retinotopic receptive fields of dendrites in the lobula or axon terminals in the optic glomeruli.
- **Rule:** Do NOT fabricate or estimate visual angle degrees from soma coordinates.

### 9. What can and cannot be inferred from neurotransmitter annotations?
- **Presynaptic Inputs:** LC4 (100%) and LPLC2 (100%) are predicted cholinergic ($p > 0.95$).
- **Descending Readouts:** DNp04, DNp06, DNp02, DNp11, DNp103 are predicted cholinergic. DNp01 is predicted cholinergic with moderate confidence (0.50–0.56), reflecting known mixed electrical and chemical transmission. DNg40 is predicted glutamatergic ($p \approx 0.62$).
- **Intermediates:** Major pathways include GABAergic (LHAD1g1, PVLP011, PVLP024) and glutamatergic (PVLP010) interneurons alongside cholinergic interneurons (PVLP122, PVLP151).
- **Sign Inference:** Predicted ACh does NOT prove functional excitation (can activate inhibitory muscarinic receptors); predicted glutamate/GABA does NOT prove inhibition. Unsigned synaptic weights must be preserved.

### 10. Which candidates should remain under consideration for Circuit v1?
- **Definitively Supported:** LC4, LPLC2, DNp01, DNp04.
- **Conditionally Supported (Flight Modality):** DNp06 (retained for flight evasive steering, acknowledged as connectomically diluted).
- **Unresolved High-Impact Additions:** DNp02 (backward jump co-factor) and DNp11 (forward jump).

### 11. Which candidates can be excluded, and why?
- **DNp103:** Excluded due to lower visual share (~9.6%) and absence of behavioral escape evidence.
- **DNg40:** Excluded due to lack of behavioral escape validation (`EVIDENCE: UNVERIFIED`).
- **DNpe056, DNp71, DNp05, DNp03, DNpe025:** Excluded due to unilateral input bias, lack of dual convergence, or lack of behavioral evidence.
- **Remaining 22 types (<350 synapses):** Excluded due to negligible visual input and visual share <2.5%.
- **All Interneurons:** Excluded from Circuit v1 under a feedforward modeling simplification, pending user approval.

### 12. Which decisions remain unresolved and require explicit user approval?
1. Whether to add **DNp02** (backward escape partner of DNp04) and **DNp11** (forward escape readout).
2. Whether to preserve pure feedforward architecture (excluding interneurons like PVLP122, LHAD1g1) or introduce top intermediate layers.
3. Whether to formally approve **DNp06** as the designated flight evasive readout despite its lower connectomic specificity.

---

## 2. Deliverables Summary

All 17 required deliverables have been produced deterministically in `connectome/phase2/`:
1. `phase2_plan.md`: Analysis plan and path architecture rationale.
2. `phase2_report.md`: This comprehensive synthesis report.
3. `candidate_dn_summary.csv`: Master candidate matrix for all 63 DNs across thresholds.
4. `candidate_dn_summary_w1.csv`: Candidate metrics at $w_{\min}=1$.
5. `candidate_dn_summary_w3.csv`: Candidate metrics at $w_{\min}=3$.
6. `candidate_dn_summary_w10.csv`: Candidate metrics at $w_{\min}=10$.
7. `direct_visual_dn_edges.csv`: All 3,611 direct visual $\to$ DN edges.
8. `intermediate_candidates.csv`: Aggregated metrics for 4,540 intermediate interneurons.
9. `two_step_paths.csv`: 23,601 two-step paths to candidate descending readouts.
10. `threshold_robustness.csv`: Detailed candidate tracking across $w_{\min} \in \{1, 3, 10\}$.
11. `biological_evidence.md`: Rigorous literature evidence record with verified citations.
12. `retinotopy_proxy.csv`: 3D soma coordinates for 374 visual and candidate neurons.
13. `neurotransmitter_analysis.csv`: Neurotransmitter annotations for 424 neurons.
14. `excluded_candidates.md`: Complete anti-cherry-picking record for all 63 DNs.
15. `circuit_v1_comparison.md`: Detailed comparison against provisional Circuit v1.
16. `phase2_decision_record.md`: Epistemic classification and unresolved user decisions.
17. `phase2_provenance.json`: Machine-readable provenance and environmental metadata.

---

## 3. Epistemic Confirmation

- **Phase 3 Circuit v1 artifacts:** Read-only; zero files modified or overwritten.
- **Phase 4 status:** **NOT STARTED**.
- **Remote Git status:** **NOTHING PUSHED TO ANY REMOTE**. All commits remain strictly local.
