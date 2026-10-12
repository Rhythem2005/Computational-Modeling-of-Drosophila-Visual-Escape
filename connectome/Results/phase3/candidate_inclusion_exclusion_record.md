# Phase 3: Candidate Inclusion & Exclusion Record

**Phase:** Phase 3
**Status:** COMPLETE & AUDITED
**Date:** 2026-09-22
**Dataset:** Drosophila MaleCNS v1.0 (`male-cns:v1.0`)

---

## 1. Anti-Cherry-Picking Principle

To prevent confirmation bias, post-hoc cherry-picking, and arbitrary exclusions:
1. **Unbiased Discovery Space:** All 1,314 descending neurons and all 311 visual projection neurons across the entire MaleCNS were evaluated.
2. **Exhaustive Candidate Accounting:** Every single descending neuron receiving direct synaptic input ($w \ge 1$) from LC4 or LPLC2 (exactly 63 neurons across 34 morphological types) is documented.
3. **Explicit Inclusion/Exclusion Rationale:** Every neuron included or excluded from Circuit v1 (Scope A) and Circuit v2 (Scope B) has an objective, documented rationale grounded in connectomic metrics and verified literature evidence.

---

## 2. Complete Inventory of All Direct Visual Descending Neurons (63 Neurons)

The table below lists all 63 direct visual descending neurons in order of total direct visual synaptic input ($w_{\min}=1$):

| Rank | Body ID | Type | Side | Total Visual ($w_1$) | Visual Share ($w_1$) | LC4 Input | LPLC2 Input | Survives $w_{10}$? | Circuit v1 Status | Circuit v2 Status | Phase 3 Epistemic Decision & Rationale |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 531898 | DNp04 | L | 8,768 | 69.57% | 6,811 | 1,957 | Yes (8,619) | **INCLUDED** | **INCLUDED** | **SUPPORTED:** Top connectomic visual share & total input; non-GF takeoff steering (Peek 2018; Dombrovski et al. 2023). |
| 2 | 10010 | DNp01 | L | 6,424 | 25.80% | 3,782 | 2,642 | Yes (6,360) | **INCLUDED** | **INCLUDED** | **SUPPORTED:** Canonical Giant Fiber; unsteered short-mode emergency jump command (Tanouye & Wyman 1980). |
| 3 | 11137 | DNp04 | R | 6,227 | 66.77% | 4,786 | 1,441 | Yes (6,046) | **INCLUDED** | **INCLUDED** | **SUPPORTED:** Bilateral pair of DNp04; massive visual drive and ~67% visual share. |
| 4 | 10001 | DNp01 | R | 4,800 | 25.83% | 2,580 | 2,220 | Yes (4,712) | **INCLUDED** | **INCLUDED** | **SUPPORTED:** Bilateral pair of DNp01; highly symmetric ~26% visual share and dual convergence. |
| 5 | 10283 | DNp103 | R | 3,050 | 10.48% | 183 | 2,867 | Yes (2,880) | **EXCLUDED** | **EXCLUDED** | **EXCLUDED (Unverified):** Strongly LPLC2-dominated; visual share diluted by ~28k dendritic arbor; `EVIDENCE: UNVERIFIED` for escape behavior. |
| 6 | 10417 | DNp103 | L | 2,350 | 8.67% | 152 | 2,198 | Yes (2,189) | **EXCLUDED** | **EXCLUDED** | **EXCLUDED (Unverified):** Bilateral pair of DNp103; lacks physiological or behavioral escape verification. |
| 7 | 10197 | DNp02 | L | 2,279 | 24.31% | 2,279 | 0 | Yes (2,240) | **EXCLUDED** | **INCLUDED** | **SUPPORTED (Circuit v2):** Synergistic co-active partner of DNp04 for backward takeoff (Peek 2018; Dombrovski et al. 2023). Added to v2 to complete motor synergy. |
| 8 | 10923 | DNg40 | R | 2,272 | 21.41% | 446 | 1,826 | Yes (2,050) | **EXCLUDED** | **EXCLUDED** | **EXCLUDED (Unverified):** Dual visual convergence, predicted glutamatergic; projects to neck/tectulum (Namiki et al. 2018), but `EVIDENCE: UNVERIFIED` for escape behavior. |
| 9 | 10259 | DNp11 | L | 2,078 | 16.24% | 2,022 | 56 | Yes (1,929) | **EXCLUDED** | **INCLUDED** | **SUPPORTED (Circuit v2):** Forward jump takeoff readout (Peek 2018; Dombrovski et al. 2023). Added to v2 to complete directional escape axis. |
| 10 | 10117 | DNp02 | R | 1,935 | 21.69% | 1,930 | 5 | Yes (1,894) | **EXCLUDED** | **INCLUDED** | **SUPPORTED (Circuit v2):** Bilateral pair of DNp02; high visual share (~22%); synergistic backward takeoff partner of DNp04. |
| 11 | 10752 | DNp03 | L | 1,828 | 15.91% | 1,827 | 1 | Yes (1,819) | **EXCLUDED** | **EXCLUDED** | **EXCLUDED (Scope):** LC4-monospecific; lacks behavioral or physiological escape evidence. |
| 12 | 10361 | DNg40 | L | 1,706 | 18.55% | 534 | 1,172 | Yes (1,360) | **EXCLUDED** | **EXCLUDED** | **EXCLUDED (Unverified):** Bilateral pair of DNg40; lacks behavioral escape validation. |
| 13 | 10106 | DNp11 | R | 1,659 | 14.55% | 1,644 | 15 | Yes (1,563) | **EXCLUDED** | **INCLUDED** | **SUPPORTED (Circuit v2):** Bilateral pair of DNp11; verified forward jump escape driver. |
| 14 | 10228 | DNp06 | L | 1,591 | 6.81% | 705 | 886 | Yes (1,090) | **INCLUDED** | **INCLUDED** | **SUPPORTED AS BASELINE:** Dual convergence; verified flight evasive turn channel (Kim et al. 2023); lower visual share (6.8%). |
| 15 | 10584 | DNp06 | R | 1,280 | 6.32% | 447 | 833 | Yes (788) | **INCLUDED** | **INCLUDED** | **SUPPORTED AS BASELINE:** Bilateral pair of DNp06; flight evasive steering channel; lower visual share (6.3%). |
| 16 | 10223 | DNpe056 | L | 876 | 10.59% | 2 | 874 | Yes (677) | **EXCLUDED** | **EXCLUDED** | **EXCLUDED (Scope):** Purely LPLC2-monospecific (>99%); lacks behavioral escape evidence. |
| 17 | 519771 | DNp71 | L | 799 | 13.24% | 2 | 797 | Yes (525) | **EXCLUDED** | **EXCLUDED** | **EXCLUDED (Scope):** Purely LPLC2-monospecific (>99%); lacks behavioral escape evidence. |
| 18 | 10732 | DNpe056 | R | 750 | 9.52% | 5 | 745 | Yes (513) | **EXCLUDED** | **EXCLUDED** | **EXCLUDED (Scope):** Purely LPLC2-monospecific (>99%); lacks behavioral escape evidence. |
| 19 | 524001 | DNp05 | L | 717 | 11.42% | 702 | 15 | Yes (604) | **EXCLUDED** | **EXCLUDED** | **EXCLUDED (Scope):** Strongly LC4-dominated (>98%); lacks behavioral escape evidence. |
| 20 | 10558 | DNp35 | R | 694 | 3.76% | 213 | 481 | Yes (197) | **EXCLUDED** | **EXCLUDED** | **EXCLUDED (Low Specificity):** Low visual share (<4%); drops significantly at $w_{10}$. |
| 21 | 10234 | DNp35 | L | 690 | 3.91% | 251 | 439 | Yes (152) | **EXCLUDED** | **EXCLUDED** | **EXCLUDED (Low Specificity):** Low visual share (<4%); drops significantly at $w_{10}$. |
| 22 | 10989 | DNp03 | R | 680 | 7.70% | 680 | 0 | Yes (546) | **EXCLUDED** | **EXCLUDED** | **EXCLUDED (Scope):** Purely LC4-monospecific; lacks behavioral escape evidence. |
| 23 | 10601 | DNpe025 | R | 655 | 7.77% | 88 | 567 | Yes (382) | **EXCLUDED** | **EXCLUDED** | **EXCLUDED (Scope):** Moderate input; LPLC2-dominated; lacks behavioral escape evidence. |
| 24 | 10449 | DNpe025 | L | 644 | 7.68% | 133 | 511 | Yes (305) | **EXCLUDED** | **EXCLUDED** | **EXCLUDED (Scope):** Moderate input; LPLC2-dominated; lacks behavioral escape evidence. |
| 25 | 11020 | DNp05 | R | 625 | 10.82% | 601 | 24 | Yes (520) | **EXCLUDED** | **EXCLUDED** | **EXCLUDED (Scope):** Strongly LC4-dominated (>96%); lacks behavioral escape evidence. |
| 26 | 11159 | DNp71 | R | 398 | 6.89% | 0 | 398 | Yes (161) | **EXCLUDED** | **EXCLUDED** | **EXCLUDED (Scope):** Purely LPLC2-monospecific; lacks behavioral escape evidence. |
| 27 | 10091 | DNpe042 | L | 279 | 1.75% | 3 | 276 | Yes (57) | **EXCLUDED** | **EXCLUDED** | **EXCLUDED (Low Input & Specificity):** Visual share < 2%; drops at $w_{10}$. |
| 28 | 12628 | DNpe042 | R | 246 | 1.44% | 0 | 246 | Yes (12) | **EXCLUDED** | **EXCLUDED** | **EXCLUDED (Low Input & Specificity):** Visual share < 2%; drops at $w_{10}$. |
| 29 | 11334 | DNpe045 | R | 195 | 2.64% | 5 | 190 | Yes (23) | **EXCLUDED** | **EXCLUDED** | **EXCLUDED (Low Input & Specificity):** <200 synapses; visual share 2.6%. |
| 30 | 11573 | DNpe021 | L | 166 | 2.86% | 166 | 0 | Yes (10) | **EXCLUDED** | **EXCLUDED** | **EXCLUDED (Low Input & Specificity):** <200 synapses; visual share 2.9%. |
| 31 | 10931 | DNpe045 | L | 139 | 1.74% | 7 | 132 | Yes (21) | **EXCLUDED** | **EXCLUDED** | **EXCLUDED (Low Input & Specificity):** <150 synapses; visual share <2%. |
| 32 | 10590 | DNpe052 | L | 114 | 2.56% | 0 | 114 | Yes (10) | **EXCLUDED** | **EXCLUDED** | **EXCLUDED (Low Input & Specificity):** <150 synapses; visual share 2.6%. |
| 33 | 575082 | DNpe021 | R | 112 | 1.92% | 61 | 51 | No (0) | **EXCLUDED** | **EXCLUDED** | **EXCLUDED (Weak Threshold Support):** Drops to 0 at $w_{10}$; visual share <2%. |
| 34 | 10244 | DNp55 | L | 107 | 1.17% | 2 | 105 | No (0) | **EXCLUDED** | **EXCLUDED** | **EXCLUDED (Weak Threshold Support):** Drops to 0 at $w_{10}$; visual share 1.2%. |
| 35 | 10783 | DNp09 | L | 104 | 1.20% | 0 | 104 | Yes (36) | **EXCLUDED** | **EXCLUDED** | **EXCLUDED (Low Input & Specificity):** Low visual share (1.2%). |
| 36 | 11133 | DNp70 | R | 71 | 0.61% | 3 | 68 | No (0) | **EXCLUDED** | **EXCLUDED** | **EXCLUDED (Negligible Specificity):** Visual share < 1%; drops at $w_{10}$. |
| 37 | 11088 | DNp55 | R | 55 | 0.68% | 0 | 55 | No (0) | **EXCLUDED** | **EXCLUDED** | **EXCLUDED (Negligible Specificity):** Visual share < 1%; drops at $w_{10}$. |
| 38 | 10580 | DNp70 | L | 50 | 0.46% | 14 | 36 | No (0) | **EXCLUDED** | **EXCLUDED** | **EXCLUDED (Negligible Specificity):** Visual share < 1%; drops at $w_{10}$. |
| 39–63 | Various | Various | L/R | <40 | <0.4% | <20 | <35 | No (0) | **EXCLUDED** | **EXCLUDED** | **EXCLUDED (Noise Level):** Negligible synaptic connectivity; drop to 0 at $w_3$ or $w_{10}$. |

---

## 3. Top Excluded Interneurons (Scope C Pathways)

The following intermediate interneurons mediate major two-step pathways from LC4/LPLC2 to descending neurons, but are excluded from Circuit v1 and Circuit v2 to preserve direct feedforward tractability:

1. **PVLP010 (glutamate):** 1,257 visual input, 1,710 output across 30 DNs. Excluded pending single-cell functional calibration.
2. **LHAD1g1 (GABA):** 1,308 visual input, 1,556 output across 26 DNs (including massive projections to DNp06 and DNp01). Excluded to avoid unconstrained inhibitory dynamics.
3. **PVLP151 (acetylcholine):** 2,530 visual input, 645 output across 23 DNs. Excluded.
4. **PVLP011 (GABA):** 7,400 visual input, 205 output across 18 DNs. Excluded.
5. **PVLP122 (acetylcholine):** 1,503 visual input, 1,003 output across 25 DNs. Excluded.
