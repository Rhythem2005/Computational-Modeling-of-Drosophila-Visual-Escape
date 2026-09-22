# Phase 3: Circuit Validation Report

**Phase:** Phase 3
**Status:** ✅ **ALL CHECKS PASSED — CIRCUITS INDEPENDENTLY VERIFIED**
**Date:** 2026-09-22
**Source Dataset:** MaleCNS v1.0 (`male-cns:v1.0`)
**Validators:**
- `connectome/scripts/phase3/verify_circuit_v1.py` (Circuit v1 Baseline)
- `connectome/scripts/phase3/verify_circuit_v2.py` (Circuit v2 Expanded Directional)

---

## 1. Executive Validation Summary

Both the baseline Circuit v1 (Scope A) and the expanded Circuit v2 (Scope B) were independently validated from scratch against the source MaleCNS v1.0 feather files.

| Circuit Version | Scope | Node Count | Edge Count ($w \ge 3$) | Build Checks | Independent Verification Checks | Status | Discrepancies |
|---|---|---|---|---|---|---|---|
| **Circuit v1** | Scope A (Minimal Direct Baseline) | 317 | 11,286 | 21 / 21 | 41 / 41 | ✅ **PASS** | 0 |
| **Circuit v2** | Scope B (Expanded Directional Takeoff) | 321 | 11,557 | 23 / 23 | 48 / 48 | ✅ **PASS** | 0 |
| **Combined** | — | — | — | **44 / 44** | **89 / 89** | ✅ **PASS** | **0** |

---

## 2. Circuit v2 Independent Verification Detail (`verify_circuit_v2.py`)

All 48 checks passed with zero tolerance (exact integer match against source data).

### Check Group 1: Artifact Files (6 checks)
- `circuit_v2_nodes.csv` exists and is valid.
- `circuit_v2_edges.csv` exists and is valid.
- `circuit_v2.json` exists and is valid.
- `circuit_v2_schema.json` exists and is valid.
- `circuit_v2_provenance.json` exists and is valid.
- `circuit_v2_build_validation.json` exists and reports `PASS`.

### Check Group 2: Source Data Integrity (3 checks)
- `body-annotations-male-cns-v1.0-minconf-0.5.feather` exists and is readable.
- `connectome-weights-male-cns-v1.0-minconf-0.5.feather` exists and is readable.
- `body-neurotransmitters-male-cns-v1.0.feather` exists and is readable.

### Check Group 3: Neuron Identifiers & Annotations (3 checks)
- All 321 neuron IDs exist in the source annotations table (0 missing).
- All 321 neuron type annotations match the source dataset exactly (0 mismatches).
- All 321 neuron hemisphere assignments (`somaSide` / instance) match source data exactly (0 mismatches).

### Check Group 4: Population Counts (8 checks)
- Total node count: exactly 321.
- Zero duplicate body IDs.
- LC4: 126 (71L, 55R).
- LPLC2: 185 (94L, 91R).
- DNp01: 2 (10010 L, 10001 R).
- DNp04: 2 (531898 L, 11137 R).
- DNp06: 2 (10228 L, 10584 R).
- DNp02: 2 (10197 L, 10117 R).
- DNp11: 2 (10259 L, 10106 R).

### Check Group 5: Edge Extraction & Exact Weight Matching (4 checks)
- The script independently re-scanned all 2,318 batches of the 1.05 GB `connectome-weights` feather file, filtered for pairs within the 321 circuit neuron IDs, aggregated duplicate rows, and thresholded at $w \ge 3$.
- **Edge Count Match:** Exactly 11,557 edges in frozen set; exactly 11,557 in re-extracted source data.
- **Extra Edges:** 0.
- **Missing Edges:** 0.
- **Weight Discrepancies:** **0 (exact integer match, tolerance = 0)**.

### Check Group 6: Threshold & Graph Integrity (3 checks)
- All edges satisfy $w \ge 3$.
- No duplicate directed `(pre, post)` pairs.
- Zero self-loops.

### Check Group 7: Readout Populations & Bilateral Symmetry (6 checks)
- Readout types are exactly `{DNp01, DNp04, DNp06, DNp02, DNp11}`.
- Every readout type possesses exactly one Left neuron and one Right neuron.

### Check Group 8: Neurotransmitter Predictions (1 check)
- 100% of the 321 neurons have predicted neurotransmitter `acetylcholine`, matching the source `body-neurotransmitters` file exactly (0 mismatches).

### Check Group 9: Provenance Checksums (3 checks)
- `body_annotations` SHA-256: `2177e246113e4cfbf1e7772ec37c6da1955ff22e8063d0b1f833101f99a9a3b2` (MATCH ✅)
- `connectome_weights` SHA-256: `e35da783d1c686b2b58b3b87cd6a403ae43bfcfba8bff28e08ef752c1a56afc1` (MATCH ✅)
- `body_neurotransmitters` SHA-256: `95c9289220663abeb3409f3ad9e5a7f8a53f8093f5139d15502cd08da8879621` (MATCH ✅)

### Check Group 10: Normalization Consistency (3 checks)
- Max raw weight is 172.
- Normalization formula $\frac{\text{weight}}{172}$ holds with maximum floating-point deviation of $1.11 \times 10^{-16}$.
- Max normalized weight equals 1.0.

### Check Group 11: Schema Compliance (2 checks)
- All node schema columns present.
- All edge schema columns present.

### Check Group 12: Phase 2 Discovery Statistics Reproduction (5 checks)
- **DNp01:** Visual input = 11,220 syn (vs. 11,224 raw discovery total; ratio = 0.9996; 4 syn pruned at $w < 3$).
- **DNp04:** Visual input = 14,985 syn (vs. 14,995 raw discovery total; ratio = 0.9993; 10 syn pruned at $w < 3$).
- **DNp06:** Visual input = 2,831 syn (vs. 2,871 raw discovery total; ratio = 0.9861; 40 syn pruned at $w < 3$).
- **DNp02:** Visual input = 4,209 syn (vs. 4,214 raw discovery total; ratio = 0.9988; 5 syn pruned at $w < 3$).
- **DNp11:** Visual input = 3,688 syn (vs. 3,737 raw discovery total; ratio = 0.9869; 49 syn pruned at $w < 3$).

---

## 3. Circuit v1 Independent Verification Detail (`verify_circuit_v1.py`)

All 41 checks passed for the archival baseline Circuit v1:
- Nodes: 317 (LC4: 126, LPLC2: 185, DNp01: 2, DNp04: 2, DNp06: 2).
- Edges: 11,286 edges ($w \ge 3$). Exact match against source feather (tolerance = 0).
- Checksums, schemas, and population counts 100% verified.

---

## 4. Discrepancies and Anomalies

**Zero discrepancies found across all checks.**

The slight differences between raw Phase 1 discovery totals and frozen circuit totals are completely and mathematically explained by the $w_{\min}=3$ filter, which pruned only noise-level 1- and 2-synapse edges while preserving $>98.6\%$ of synaptic weight across all descending readout channels.

---

## 5. Certification

Both Circuit v1 and Circuit v2 are certified as fully reproducible, mathematically verified connectomic circuits ready for biophysical simulation modeling.
