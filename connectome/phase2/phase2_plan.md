# Phase 2 Analysis Plan: Candidate Circuit Analysis & Biological Validation

**Phase:** Phase 2  
**Status:** PLAN APPROVED & IN EXECUTION  
**Date:** 2026-09-22  
**Corpus / Dataset:** Drosophila MaleCNS v1.0 (`male-cns:v1.0`)  

---

## 1. Directory Convention and Path Architecture

Following the repository cleanup and reorganization:
- **Phase-scoped deliverables & artifacts** are organized under `connectome/<phase>/` (mirroring `connectome/phase3/`).
- **Phase scripts** are organized under `connectome/scripts/<phase>/` (mirroring `connectome/scripts/phase1/` and `connectome/scripts/phase3/`).
- **Raw datasets** reside in `connectome/data/raw/`.
- **Phase 1 discovery outputs** reside in `connectome/data/discovery/`.

To preserve architectural symmetry with Phase 3 (which contains `connectome/phase3/specification.md`, `circuit_v1.json`, etc.), all Phase 2 deliverables, reports, and tables are located in:
```
connectome/phase2/
```
Analysis and verification scripts are located in:
```
connectome/scripts/phase2/
```
No redundant `connectome/data/phase2/` directory is created.

---

## 2. Current Inputs and Source Datasets

### Pinned Source Datasets
The analysis operates directly on the pinned MaleCNS v1.0 dataset located in `connectome/data/raw/`:
1. **Body Annotations:** `connectome/data/raw/annotations/body-annotations-male-cns-v1.0-minconf-0.5.feather`
   - SHA256: `2177e246113e4cfbf1e7772ec37c6da1955ff22e8063d0b1f833101f99a9a3b2`
   - Size: 14,483,314 bytes (211,577 rows)
2. **Connectome Weights:** `connectome/data/raw/connectivity/connectome-weights-male-cns-v1.0-minconf-0.5.feather`
   - SHA256: `e35da783d1c686b2b58b3b87cd6a403ae43bfcfba8bff28e08ef752c1a56afc1`
   - Size: 1,051,241,946 bytes (151,856,684 rows)
3. **Body Neurotransmitters:** `connectome/data/raw/neurotransmitters/body-neurotransmitters-male-cns-v1.0.feather`
   - SHA256: `95c9289220663abeb3409f3ad9e5a7f8a53f8093f5139d15502cd08da8879621`
   - Size: 43,282,834 bytes (1,835,518 rows)

### Existing Phase 1 Discovery Artifacts (Read-Only)
- `connectome/data/discovery/visual_descending_edges.csv` (3,611 rows)
- `connectome/data/discovery/visual_descending_targets.csv` (63 rows)
- `connectome/data/discovery/two_step_visual_descending_paths.csv` (61,959 rows)
- `connectome/data/discovery/two_step_visual_descending_by_type.csv`
- `connectome/data/discovery/common_visual_targets.csv`
- `connectome/data/discovery/discovery_summary.json`
- `connectome/data/discovery/research_queue.md`

### Phase 3 Provisional Artifacts (Read-Only Comparison Baseline)
- `connectome/phase3/circuit_v1.json`
- `connectome/phase3/circuit_v1_nodes.csv`
- `connectome/phase3/circuit_v1_edges.csv`
- `connectome/phase3/specification.md`
- `connectome/phase3/decision_record.md`
- `connectome/phase3/excluded_candidates.md`
- `connectome/phase3/provenance.json`

---

## 3. Version-Consistency Check and Data Integrity Audit

### Checksums and Provenance Alignment
The SHA256 checksums of the three pinned raw feather files in `connectome/data/raw/` match the hashes recorded in `connectome/phase3/provenance.json` exactly.

### Phase 1 vs. Source Verification: Key Integrity Findings
1. **Direct Visual Edges:** Scanning raw connectivity from LC4 (126 neurons) and LPLC2 (185 neurons) to descending neurons (`superclass == 'descending_neuron'`, 1,314 neurons) yields exactly 3,611 edges targeting 63 descending neurons. This confirms that Phase 1's edge discovery was extracted from this exact source data.
2. **Threshold Difference (w_min=1 vs w_min=3):** Phase 1 discovery recorded all edges including single- and double-synapse connections ($w \ge 1$), whereas Phase 3 applied $w \ge 3$. At $w \ge 3$, several weak connections drop out (e.g. DNpe056 loses LC4 input). Phase 2 will recompute across all three thresholds ($w_{\min} \in \{1, 3, 10\}$) directly from source.
3. **Missing Denominators in Phase 1:** Phase 1 did not compute total incoming dendritic inputs for all candidate descending neurons. As a result, visual-input share (connectomic specificity) was never calculated. Phase 2 recomputes total incoming weight across the entire 151.8M-edge connectome for all candidates.
4. **Data-Integrity Distinction:** Any discrepancies between Phase 1 discovery numbers and Phase 2 recomputed tables are classified strictly as Phase 1 thresholding or aggregation discrepancies, not as Phase 2 biological findings.

---

## 4. Planned Analyses

### A. Candidate Descending Neuron Analysis
- Population: ALL 63 descending neurons receiving direct LC4 and/or LPLC2 input.
- Metrics per neuron:
  - `bodyId`, `type`, `somaSide` (L/R)
  - `LC4_weight`, `LPLC2_weight`, `total_visual_weight`
  - `total_incoming_weight` (sum of all incoming synapses in MaleCNS)
  - `visual_share` = `total_visual_weight / total_incoming_weight`
  - `LC4_fraction_visual` = `LC4_weight / total_visual_weight`
  - `LPLC2_fraction_visual` = `LPLC2_weight / total_visual_weight`
  - `LC4_presynaptic_count` (unique LC4 partners)
  - `LPLC2_presynaptic_count` (unique LPLC2 partners)
  - `direct_visual_partners_total`
  - Bilateral / asymmetry metrics
  - Rank orders under each metric (total visual, visual share, LC4 input, LPLC2 input)

### B. Threshold Robustness ($w_{\min} \in \{1, 3, 10\}$)
- Recompute edge counts, total visual weights, active candidates, and rankings for:
  - $w_{\min} = 1$ (all detected synapses)
  - $w_{\min} = 3$ (standard noise filter used in Phase 1/Phase 3)
  - $w_{\min} = 10$ (high-confidence core connections)
- Track which candidates appear, drop out, or change ranking across thresholds.

### C. Direct Pathway Analysis
- Full edge-level table (`direct_visual_dn_edges.csv`) linking `body_pre`, `pre_type`, `body_post`, `post_type`, `weight`, `threshold`, and population types.
- Aggregated summaries by DN type and individual neuron.

### D. Two-Step / Intermediate Pathway Analysis
- Analyze pathways: $LC4 \to X \to DN$, $LPLC2 \to X \to DN$, and $LC4/LPLC2 \to X \to DN$.
- Candidate intermediate selection based on:
  - Total visual input received from LC4/LPLC2
  - Output weight to candidate descending neurons
  - Specificity and pathway weight product: $\text{PathScore} = W(\text{Visual} \to X) \times W(X \to DN)$
  - Threshold robustness of intermediate edges
- Explicit documentation of the path score formula and components.

### E. Candidate Specificity
- Contrast absolute visual input vs. relative visual share.
- Distinguish connectomic specificity from behavioral command authority.

### F. Biological / Literature Evidence Review
- Focused review of literature for:
  - LC4 (looming velocity detector, Klapoetke et al. 2017, von Reyn et al. 2014, 2017)
  - LPLC2 (radial motion opponency, looming size detector, Klapoetke et al. 2017)
  - DNp01 (Giant Fiber, short-mode escape, Tanouye & Wyman 1980, Allen et al. 2006, von Reyn et al. 2014)
  - DNp04 (LC4DN, backward takeoff / postural steering, Peek 2018, Dombrovski et al. 2023)
  - DNp06 (evasive flight turns, Kim et al. 2023)
  - DNp02 (LC4DN, backward jumping, Peek 2018, Dombrovski et al. 2023)
  - DNp11 (forward jump / steering, Peek 2018)
  - DNg40, DNp103 (morphology, connectome characterization, Namiki et al. 2018)
- Every citation verified through web search or repository documents; unconfirmed claims flagged as `EVIDENCE: UNVERIFIED`.

### G. Retinotopy Analysis
- Audit `body-annotations` for optic lobe coordinates (`assignedOlHex1`, `assignedOlHex2` are null).
- Analyze `somaLocation` 3D distributions as an anatomical proxy.
- State explicitly: `RETINOTOPY: NOT AVAILABLE` for visual-angle mapping; explain the missing biological projection coordinates.

### H. Neurotransmitter Analysis
- Join predicted neurotransmitters from `body-neurotransmitters-male-cns-v1.0.feather`.
- Report predicted NT, confidence, and consensus for all candidate types.
- Explicitly emphasize: predicted ACh does not guarantee functional excitation (nicotinic vs muscarinic receptors), and predicted GABA/glutamate does not guarantee functional inhibition.

### I. Unknown and Null Type Handling
- Quantify descending neurons with null type (4 neurons: 11851, 13539, 13964, 55579).
- Quantify intermediate neurons with UNKNOWN type (573 shared targets).
- Document impact on candidate discovery and justification for exclusion.

### J. Anti-Cherry-Picking Analysis & Excluded Candidates
- Complete matrix of all 63 direct visual DNs.
- Detailed, objective exclusion reasons for every non-selected candidate.
- Unresolved scope boundaries marked as `UNRESOLVED — REQUIRES USER APPROVAL`.

### K. Comparison with Provisional Circuit v1
- Detailed side-by-side comparison of Circuit v1 (LC4, LPLC2, DNp01, DNp04, DNp06) vs Phase 2 quantitative and biological findings.
- Identify strengths, vulnerabilities (e.g. DNp06 visual weight vs DNp103/DNp02), and excluded high-weight candidates.

### L. Epistemic Classification and Decision Record
- Classify all components as: SUPPORTED, POSSIBLE, UNRESOLVED, or NOT SUPPORTED.
- Maintain provisional status until explicit user sign-off.

---

## 5. Output Deliverables Manifest (`connectome/phase2/`)

1. `phase2_plan.md` (this file)
2. `phase2_report.md`
3. `candidate_dn_summary.csv`
4. `candidate_dn_summary_w1.csv`
5. `candidate_dn_summary_w3.csv`
6. `candidate_dn_summary_w10.csv`
7. `direct_visual_dn_edges.csv`
8. `intermediate_candidates.csv`
9. `two_step_paths.csv`
10. `threshold_robustness.csv`
11. `biological_evidence.md`
12. `retinotopy_proxy.csv` (accompanied by explicit `RETINOTOPY: NOT AVAILABLE` documentation)
13. `neurotransmitter_analysis.csv`
14. `excluded_candidates.md`
15. `circuit_v1_comparison.md`
16. `phase2_decision_record.md`
17. `phase2_provenance.json`

---

## 6. Validation Strategy

1. **Deterministic Execution:** Single standalone script `connectome/scripts/phase2/analyze.py` that reads only the pinned raw feather files and generates all CSVs and JSON provenance.
2. **Verification Suite:** `connectome/scripts/phase2/verify_phase2.py` verifying:
   - File existence and non-emptiness for all 17 artifacts
   - Candidate counts across thresholds ($w_{\min}=1, 3, 10$)
   - Edge sum consistency (edges sum to candidate totals)
   - Visual share range ($0 \le \text{visual\_share} \le 1$)
   - Zero modifications to `connectome/phase3/*`
3. **Phase 4 Guardrail:** No simulation, behavioral training, or visual encoding code implemented.
4. **Git Hygiene:** Clean local commits on branch `phase2-candidate-analysis`, no push to remote.
