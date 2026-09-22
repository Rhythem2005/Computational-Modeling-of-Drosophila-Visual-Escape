# Circuit v1 — Validation Report

**Date:** 2026-09-22
**Validator:** `verify_circuit_v1.py` (independent verification, separate from build script)

---

## Summary

| Metric | Result |
|--------|--------|
| **Overall Status** | ✅ **PASS** |
| Build-time checks | 21/21 passed |
| Independent verification checks | 41/41 passed |
| Total checks | 62/62 passed |
| Failures | 0 |

---

## Build-Time Validation (phase3_freeze.py)

All 21 checks passed during circuit construction:

| # | Check | Result |
|---|-------|--------|
| 1 | Total node count is 317 | ✅ |
| 2 | No duplicate bodyIds | ✅ |
| 3 | LC4 count = 126 | ✅ |
| 4 | LPLC2 count = 185 | ✅ |
| 5 | DNp01 count = 2 | ✅ |
| 6 | DNp04 count = 2 | ✅ |
| 7 | DNp06 count = 2 | ✅ |
| 8 | DNp01 has both L and R neurons | ✅ |
| 9 | DNp04 has both L and R neurons | ✅ |
| 10 | DNp06 has both L and R neurons | ✅ |
| 11 | Circuit has edges | ✅ |
| 12 | All edge endpoints are circuit neurons | ✅ |
| 13 | All edges have weight ≥ 3 | ✅ |
| 14 | No self-loop edges | ✅ |
| 15 | No duplicate (pre, post) pairs | ✅ |
| 16 | DNp01 receives visual input (308 edges) | ✅ |
| 17 | DNp04 receives visual input (304 edges) | ✅ |
| 18 | Max normalized weight is 1.0 | ✅ |
| 19 | All normalized weights are non-negative | ✅ |
| 20 | All normalized weights are ≤ 1.0 | ✅ |
| 21 | All nodes have NT prediction | ✅ |

---

## Independent Verification (verify_circuit_v1.py)

All 41 checks passed. The verification script independently re-extracts data from the source feather files and compares against frozen artifacts.

### Section 1: Artifact Files (6 checks)
All 6 required artifact files exist in `connectome/phase3/`.

### Section 2: Source Data (3 checks)
All 3 source feather files exist.

### Section 3: Neuron ID Verification (1 check)
All 317 frozen neuron IDs exist in the source annotations file. Zero missing.

### Section 4: Neuron Type Verification (1 check)
All neuron types in the frozen circuit exactly match the source annotations. Zero mismatches.

### Section 5: Neuron Side Verification (1 check)
All neuron hemisphere assignments match source `somaSide` annotations. Zero mismatches.

### Section 6: Population Counts (7 checks)
Total node count = 317. No duplicate bodyIds. All 5 type counts match expected values.

### Section 7: Edge Weight Verification — EXACT MATCH (4 checks)

**This is the critical verification.** The script independently re-extracts all edges among the 317 circuit neurons from the 1 GB connectivity feather file, aggregates them, applies w_min=3, and compares:

| Metric | Result |
|--------|--------|
| Frozen edge count | 11,286 |
| Source re-extracted edge count | 11,286 |
| Extra edges in frozen set | 0 |
| Missing edges in frozen set | 0 |
| Weight mismatches | **0 (exact match, tolerance=0)** |

**Weight match rule:** Exact integer match. No tolerance applied. Every frozen weight is identical to the source-recomputed weight.

### Section 8–9: Threshold and Integrity (4 checks)
All edges have weight ≥ 3. No duplicate (pre, post) pairs. No self-loops.

### Section 10: Readout Populations (4 checks)
Readout types are exactly {DNp01, DNp04, DNp06}. All three have L/R pairs.

### Section 11: Neurotransmitter Verification (1 check)
All NT predictions match the source `body-neurotransmitters` feather file. Zero mismatches.

### Section 12: Provenance Checksums (3 checks)
SHA-256 checksums of all three source feather files match the recorded provenance values.

| File | Recorded SHA-256 | Current SHA-256 | Match |
|------|-----------------|-----------------|-------|
| body-annotations | `2177e246113e4cfb...` | `2177e246113e4cfb...` | ✅ |
| connectome-weights | `e35da783d1c686b2...` | `e35da783d1c686b2...` | ✅ |
| body-neurotransmitters | `95c9289220663abe...` | `95c9289220663abe...` | ✅ |

### Section 13: Normalization (2 checks)
Normalization is mathematically consistent: max difference between `weight/max_weight` and stored `weight_normalized` is 1.11e-16 (floating-point epsilon).

### Section 14: Schema (2 checks)
All schema-declared node and edge columns are present in the CSV files.

### Section 15: Phase 2 Statistics Reproduction (3 checks)

Frozen circuit visual input totals compared against Phase 1 discovery totals:

| Readout | Frozen Total | Discovery Total | Ratio | Explanation |
|---------|-------------|----------------|-------|-------------|
| DNp01 | 11,220 | 11,224 | 0.9996 | 4 syn pruned by w_min=3 |
| DNp04 | 14,985 | 14,995 | 0.9993 | 10 syn pruned by w_min=3 |
| DNp06 | 2,831 | 2,871 | 0.9861 | 40 syn pruned by w_min=3 |

All ratios are ≥ 0.98, confirming that the w_min=3 threshold pruned only very weak edges. The differences are entirely accounted for by edge-weight filtering.

---

## Data Provenance Record

| Item | Value |
|------|-------|
| Dataset | MaleCNS v1.0 (`male-cns:v1.0`) |
| Server | https://neuprint.janelia.org |
| Annotations file | `body-annotations-male-cns-v1.0-minconf-0.5.feather` (14.5 MB) |
| Annotations SHA-256 | `2177e246113e4cfbf1e7772ec37c6da1955ff22e8063d0b1f833101f99a9a3b2` |
| Connectivity file | `connectome-weights-male-cns-v1.0-minconf-0.5.feather` (1.05 GB) |
| Connectivity SHA-256 | `e35da783d1c686b2b58b3b87cd6a403ae43bfcfba8bff28e08ef752c1a56afc1` |
| NT file | `body-neurotransmitters-male-cns-v1.0.feather` (43.3 MB) |
| NT SHA-256 | `95c9289220663abeb3409f3ad9e5a7f8a53f8093f5139d15502cd08da8879621` |
| w_min threshold | 3 |
| pandas version | 3.0.6 |
| pyarrow version | 25.0.1 |
| numpy version | 2.5.3 |

---

## Discrepancies Found

**None.** All checks passed with zero discrepancies.

The only noted variance is the expected difference between discovery totals (w_min=1) and frozen circuit totals (w_min=3), which is fully explained by threshold filtering and amounts to <2% of total weight for all readouts.
