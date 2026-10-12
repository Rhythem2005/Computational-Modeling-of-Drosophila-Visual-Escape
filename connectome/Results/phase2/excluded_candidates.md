# Phase 2: Complete Excluded Candidate & Anti-Cherry-Picking Record

**Phase:** Phase 2  
**Status:** COMPLETE  
**Date:** 2026-09-22  
**Dataset:** Drosophila MaleCNS v1.0 (`male-cns:v1.0`)  

---

## 1. Anti-Cherry-Picking Principle and Methodology

In Phase 1 and provisional Phase 3 artifacts, Circuit v1 was restricted to {LC4, LPLC2, DNp01, DNp04, DNp06} and all other descending neurons and interneurons were labeled as "excluded" without a documented Phase 2 evaluation.

To prevent confirmation bias, post-hoc cherry-picking, and arbitrary exclusions:
1. **The Discovery Universe is the Entire Connectome:** All 1,314 descending neurons and all 311 visual projection neurons were evaluated objectively.
2. **Every Candidate Direct Visual DN is Accounted For:** Exactly 63 descending neurons (spanning 34 morphological types) receive direct synaptic input from LC4 and/or LPLC2 ($w \ge 1$).
3. **Objective, Measurable Metrics:** Every candidate is characterized by absolute visual input, visual share ($\text{visual\_weight} / \text{total\_incoming}$), convergence ratio ($\text{LC4} : \text{LPLC2}$), threshold stability ($w_{\min} \in \{1, 3, 10\}$), and verified literature evidence.
4. **Epistemic Discipline:** If an exclusion is based on project scope rather than connectomic or biological negation, it is explicitly classified as **`UNRESOLVED — REQUIRES USER APPROVAL`**.

---

## 2. Complete Inventory of All Direct Visual Descending Neurons (63 Neurons, 34 Types)

The table below lists all 63 descending neurons receiving direct LC4 or LPLC2 input at $w_{\min}=1$, sorted by total visual input:

| Rank | Body ID | Type | Side | Total Visual ($w_1$) | Visual Share ($w_1$) | LC4 Input | LPLC2 Input | Survives $w_{10}$? | Receives Both ($w_3$)? | Current Circuit v1 Status | Epistemic Decision / Exclusion Rationale |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 531898 | DNp04 | L | 8,768 | 69.57% | 6,811 | 1,957 | Yes (8,619) | Yes | **INCLUDED** | **SUPPORTED:** Top connectomic visual share & total input; verified backward takeoff role (Peek 2018). |
| 2 | 10010 | DNp01 | L | 6,424 | 25.80% | 3,782 | 2,642 | Yes (6,360) | Yes | **INCLUDED** | **SUPPORTED:** Canonical Giant Fiber; verified short-mode escape trigger (Tanouye & Wyman 1980). |
| 3 | 11137 | DNp04 | R | 6,227 | 66.77% | 4,786 | 1,441 | Yes (6,046) | Yes | **INCLUDED** | **SUPPORTED:** Bilateral pair of DNp04; massive visual input and ~67% visual share. |
| 4 | 10001 | DNp01 | R | 4,800 | 25.83% | 2,580 | 2,220 | Yes (4,712) | Yes | **INCLUDED** | **SUPPORTED:** Bilateral pair of DNp01 (GF_R); symmetric ~26% visual share. |
| 5 | 10283 | DNp103 | R | 3,050 | 10.48% | 183 | 2,867 | Yes (2,880) | Yes | **EXCLUDED** | **UNRESOLVED — REQUIRES USER APPROVAL:** High visual input (LPLC2-dominated); lower visual share (10.5%); unverified escape behavior. |
| 6 | 10417 | DNp103 | L | 2,350 | 8.67% | 152 | 2,198 | Yes (2,189) | Yes | **EXCLUDED** | **UNRESOLVED — REQUIRES USER APPROVAL:** Bilateral pair of DNp103; high visual input but low visual share (8.7%). |
| 7 | 10197 | DNp02 | L | 2,279 | 24.31% | 2,279 | 0 | Yes (2,240) | No | **EXCLUDED** | **UNRESOLVED — REQUIRES USER APPROVAL:** High visual input (~24% share); verified backward escape role (Peek 2018); excluded solely due to LC4 monospecificity (0 LPLC2 input). |
| 8 | 10923 | DNg40 | R | 2,272 | 21.41% | 446 | 1,826 | Yes (2,050) | Yes | **EXCLUDED** | **UNRESOLVED — REQUIRES USER APPROVAL:** High visual input (~21% share); dual convergence; predicted glutamatergic; unverified behavioral role. |
| 9 | 10259 | DNp11 | L | 2,078 | 16.24% | 2,022 | 56 | Yes (1,929) | Yes | **EXCLUDED** | **UNRESOLVED — REQUIRES USER APPROVAL:** High visual input (~16% share); verified forward jump escape role (Peek 2018); highly LC4-dominated (97% LC4). |
| 10 | 10117 | DNp02 | R | 1,935 | 21.69% | 1,930 | 5 | Yes (1,894) | No | **EXCLUDED** | **UNRESOLVED — REQUIRES USER APPROVAL:** Bilateral pair of DNp02; high visual input (~22% share); LC4-dominated. |
| 11 | 10752 | DNp03 | L | 1,828 | 15.91% | 1,827 | 1 | Yes (1,819) | No | **EXCLUDED** | **EXCLUDED (Scope):** LC4-monospecific; unverified escape behavior. |
| 12 | 10361 | DNg40 | L | 1,706 | 18.55% | 534 | 1,172 | Yes (1,360) | Yes | **EXCLUDED** | **UNRESOLVED — REQUIRES USER APPROVAL:** Bilateral pair of DNg40; dual convergence; unverified behavioral role. |
| 13 | 10106 | DNp11 | R | 1,659 | 14.55% | 1,644 | 15 | Yes (1,563) | No | **EXCLUDED** | **UNRESOLVED — REQUIRES USER APPROVAL:** Bilateral pair of DNp11; verified forward jump role; LC4-dominated. |
| 14 | 10228 | DNp06 | L | 1,591 | 6.81% | 705 | 886 | Yes (1,090) | Yes | **INCLUDED** | **SUPPORTED:** Dual convergence; verified evasive flight steering role (Kim et al. 2023); lower visual share (6.8%). |
| 15 | 10584 | DNp06 | R | 1,280 | 6.32% | 447 | 833 | Yes (788) | Yes | **INCLUDED** | **SUPPORTED:** Bilateral pair of DNp06; verified flight evasive turn channel; lower visual share (6.3%). |
| 16 | 10223 | DNpe056 | L | 876 | 10.59% | 2 | 874 | Yes (748) | No | **EXCLUDED** | **EXCLUDED (Scope):** Strongly LPLC2-monospecific (>99%); unverified behavioral role. |
| 17 | 519771 | DNp71 | R | 799 | 10.37% | 2 | 797 | Yes (761) | No | **EXCLUDED** | **EXCLUDED (Scope):** Strongly LPLC2-monospecific (>99%); unverified behavioral role. |
| 18 | 10732 | DNpe056 | R | 750 | 10.51% | 5 | 745 | Yes (640) | No | **EXCLUDED** | **EXCLUDED (Scope):** Strongly LPLC2-monospecific (>99%); unverified behavioral role. |
| 19 | 524001 | DNp05 | R | 717 | 10.99% | 702 | 15 | Yes (636) | Yes | **EXCLUDED** | **EXCLUDED (Scope):** Strongly LC4-dominated (>98%); unverified behavioral role. |
| 20 | 10558 | DNp35 | L | 694 | 3.86% | 213 | 481 | Yes (197) | Yes | **EXCLUDED** | **EXCLUDED (Low Specificity):** Low visual share (<4%); receives dual input but diluted across large arbor. |
| 21 | 10234 | DNp35 | R | 690 | 3.81% | 251 | 439 | Yes (152) | Yes | **EXCLUDED** | **EXCLUDED (Low Specificity):** Bilateral pair of DNp35; low visual share (<4%). |
| 22 | 10989 | DNp03 | R | 680 | 8.87% | 680 | 0 | Yes (654) | No | **EXCLUDED** | **EXCLUDED (Scope):** LC4-monospecific (100%); unverified behavioral role. |
| 23 | 10601 | DNpe025 | L | 655 | 8.01% | 88 | 567 | Yes (382) | Yes | **EXCLUDED** | **EXCLUDED (Scope):** Moderate input; LPLC2-dominated; unverified behavioral role. |
| 24 | 10449 | DNpe025 | R | 644 | 7.45% | 133 | 511 | Yes (248) | Yes | **EXCLUDED** | **EXCLUDED (Scope):** Moderate input; LPLC2-dominated; unverified behavioral role. |
| 25 | 11020 | DNp05 | L | 625 | 11.27% | 601 | 24 | Yes (559) | Yes | **EXCLUDED** | **EXCLUDED (Scope):** Strongly LC4-dominated (>96%); unverified behavioral role. |
| 26 | 11159 | DNp71 | L | 398 | 9.49% | 0 | 398 | Yes (374) | No | **EXCLUDED** | **EXCLUDED (Scope):** Purely LPLC2-monospecific (100%); unverified behavioral role. |
| 27 | 10091 | DNpe042 | L | 279 | 1.63% | 3 | 276 | Yes (222) | No | **EXCLUDED** | **EXCLUDED (Low Input & Specificity):** Low visual share (<2%); LPLC2-monospecific. |
| 28 | 12628 | DNpe042 | R | 246 | 1.55% | 0 | 246 | Yes (199) | No | **EXCLUDED** | **EXCLUDED (Low Input & Specificity):** Low visual share (<2%); LPLC2-monospecific. |
| 29 | 11334 | DNpe045 | L | 195 | 2.50% | 5 | 190 | Yes (139) | Yes | **EXCLUDED** | **EXCLUDED (Low Input & Specificity):** <200 synapses; visual share 2.5%. |
| 30 | 11573 | DNpe021 | L | 166 | 2.87% | 166 | 0 | Yes (134) | No | **EXCLUDED** | **EXCLUDED (Low Input & Specificity):** <200 synapses; LC4-monospecific. |
| 31 | 10931 | DNpe045 | R | 139 | 1.88% | 7 | 132 | Yes (100) | Yes | **EXCLUDED** | **EXCLUDED (Low Input & Specificity):** <150 synapses; visual share <2%. |
| 32 | 10590 | DNpe052 | R | 114 | 1.94% | 0 | 114 | No (0) | No | **EXCLUDED** | **EXCLUDED (Weak Threshold Support):** Drops to 0 at $w_{\min}=10$; visual share <2%. |
| 33 | 575082 | DNpe021 | R | 112 | 1.91% | 61 | 51 | No (0) | No | **EXCLUDED** | **EXCLUDED (Weak Threshold Support):** Drops to 0 at $w_{\min}=10$; visual share <2%. |
| 34 | 10244 | DNp55 | L | 107 | 1.25% | 2 | 105 | Yes (64) | No | **EXCLUDED** | **EXCLUDED (Low Input & Specificity):** Low visual share (1.2%). |
| 35 | 10783 | DNp09 | L | 104 | 1.05% | 0 | 104 | Yes (74) | No | **EXCLUDED** | **EXCLUDED (Low Input & Specificity):** Low visual share (1.0%). |
| 36 | 11133 | DNp70 | R | 71 | 0.63% | 3 | 68 | Yes (39) | No | **EXCLUDED** | **EXCLUDED (Negligible Specificity):** Visual share < 1%. |
| 37 | 11088 | DNp55 | R | 55 | 0.60% | 0 | 55 | Yes (23) | No | **EXCLUDED** | **EXCLUDED (Negligible Specificity):** Visual share < 1%. |
| 38 | 10580 | DNp70 | L | 50 | 0.44% | 14 | 36 | No (0) | No | **EXCLUDED** | **EXCLUDED (Negligible Specificity):** Visual share < 1%; drops at $w_{10}$. |
| 39 | 10296 | DNge054 | R | 37 | 0.38% | 4 | 33 | Yes (16) | Yes | **EXCLUDED** | **EXCLUDED (Negligible Input):** <40 synapses; visual share 0.38%. |
| 40 | 10377 | DNge054 | L | 34 | 0.36% | 4 | 30 | Yes (13) | Yes | **EXCLUDED** | **EXCLUDED (Negligible Input):** <40 synapses; visual share 0.36%. |
| 41 | 10957 | DNp69 | R | 33 | 0.22% | 16 | 17 | No (0) | Yes | **EXCLUDED** | **EXCLUDED (Negligible Input):** <40 synapses; drops at $w_{10}$. |
| 42 | 11632 | DNpe052 | L | 31 | 0.45% | 0 | 31 | No (0) | No | **EXCLUDED** | **EXCLUDED (Negligible Input):** <40 synapses; drops at $w_{10}$. |
| 43 | 536048 | DNp27 | L | 23 | 0.26% | 5 | 18 | No (0) | No | **EXCLUDED** | **EXCLUDED (Negligible Input):** <25 synapses; drops at $w_{10}$. |
| 44 | 10063 | DNp27 | R | 22 | 0.27% | 4 | 18 | No (0) | No | **EXCLUDED** | **EXCLUDED (Negligible Input):** <25 synapses; drops at $w_{10}$. |
| 45 | 33037 | DNp69 | L | 19 | 0.21% | 17 | 2 | No (0) | No | **EXCLUDED** | **EXCLUDED (Negligible Input):** <20 synapses; drops at $w_{10}$. |
| 46 | 10118 | DNb05 | L | 15 | 0.08% | 15 | 0 | No (0) | No | **EXCLUDED** | **EXCLUDED (Negligible Input):** 15 synapses; drops at $w_{10}$. |
| 47 | 10065 | DNb05 | R | 15 | 0.08% | 15 | 0 | No (0) | No | **EXCLUDED** | **EXCLUDED (Negligible Input):** 15 synapses; drops at $w_{10}$. |
| 48 | 11290 | DNp66 | R | 9 | 0.15% | 9 | 0 | No (0) | No | **EXCLUDED** | **EXCLUDED (Negligible Input):** 9 synapses; drops at $w_{10}$. |
| 49 | 10030 | pIP1 | L | 8 | 0.03% | 8 | 0 | No (0) | No | **EXCLUDED** | **EXCLUDED (Non-DN / Courtship):** pIP1 is male-specific courtship interneuron; negligible input. |
| 50 | 10713 | DNp42 | L | 7 | 0.07% | 7 | 0 | No (0) | No | **EXCLUDED** | **EXCLUDED (Negligible Input):** 7 synapses; drops at $w_{10}$. |
| 51 | 11177 | DNp09 | R | 7 | 0.08% | 0 | 7 | No (0) | No | **EXCLUDED** | **EXCLUDED (Negligible Input):** 7 synapses; drops at $w_{10}$. |
| 52 | 10280 | DNp47 | R | 6 | 0.16% | 5 | 1 | No (0) | No | **EXCLUDED** | **EXCLUDED (Negligible Input):** 6 synapses; drops at $w_{10}$. |
| 53 | 522345 | DNpe037 | R | 5 | 0.15% | 0 | 5 | No (0) | No | **EXCLUDED** | **EXCLUDED (Negligible Input):** 5 synapses; drops at $w_{10}$. |
| 54 | 11513 | DNp07 | R | 4 | 0.07% | 4 | 0 | No (0) | No | **EXCLUDED** | **EXCLUDED (Negligible Input):** 4 synapses; drops at $w_{10}$. |
| 55 | 506334 | DNp42 | R | 4 | 0.05% | 4 | 0 | No (0) | No | **EXCLUDED** | **EXCLUDED (Negligible Input):** 4 synapses; drops at $w_{10}$. |
| 56 | 11063 | DNge032 | R | 4 | 0.14% | 0 | 4 | No (0) | No | **EXCLUDED** | **EXCLUDED (Negligible Input):** 4 synapses; drops at $w_{10}$. |
| 57 | 10342 | DNc02 | R | 3 | 0.14% | 0 | 3 | No (0) | No | **EXCLUDED** | **EXCLUDED (Negligible Input):** 3 synapses; drops at $w_{10}$. |
| 58 | 10068 | DNp30 | R | 2 | 0.03% | 2 | 0 | No (0) | No | **EXCLUDED** | **EXCLUDED (Noise Level):** 2 synapses; drops at $w_3$. |
| 59 | 10143 | DNp30 | L | 2 | 0.03% | 2 | 0 | No (0) | No | **EXCLUDED** | **EXCLUDED (Noise Level):** 2 synapses; drops at $w_3$. |
| 60 | 10705 | DNc02 | L | 2 | 0.12% | 2 | 0 | No (0) | No | **EXCLUDED** | **EXCLUDED (Noise Level):** 2 synapses; drops at $w_3$. |
| 61 | 12218 | DNpe031 | L | 2 | 0.03% | 0 | 2 | No (0) | No | **EXCLUDED** | **EXCLUDED (Noise Level):** 2 synapses; drops at $w_3$. |
| 62 | 12222 | DNpe031 | R | 1 | 0.02% | 0 | 1 | No (0) | No | **EXCLUDED** | **EXCLUDED (Noise Level):** 1 synapse; drops at $w_3$. |
| 63 | 10038 | pIP1 | R | 1 | 0.00% | 1 | 0 | No (0) | No | **EXCLUDED** | **EXCLUDED (Noise Level):** 1 synapse; drops at $w_3$. |

---

## 3. High-Priority Excluded Candidates Requiring User Decision

Four descending neuron populations rank substantially higher than the included candidate **DNp06** in absolute visual input, visual share, or behavioral relevance:

### 1. DNp02 (Rank 4, 4,214 visual synapses, ~23% visual share)
- **Status:** EXCLUDED from Circuit v1.
- **Why it was excluded:** Strictly receives LC4 input (over 4,200 synapses; 0 LPLC2 input at $w \ge 10$). Circuit v1 prioritized dual convergence from both LC4 and LPLC2.
- **Why exclusion is problematic:** In published literature (Peek 2018; Dombrovski et al. 2023 *Nature*), DNp02 is the obligate co-factor with DNp04 for directing backward takeoff! Excluding DNp02 while including DNp04 leaves DNp04's primary behavioral motor synergy incomplete.
- **Decision Status:** `UNRESOLVED — REQUIRES USER APPROVAL: Should DNp02 be included in Circuit v1 to model backward takeoff steering, despite lacking LPLC2 input?`

### 2. DNp11 (Rank 6, 3,737 visual synapses, ~15.4% visual share)
- **Status:** EXCLUDED from Circuit v1.
- **Why it was excluded:** Strongly LC4-dominated (98% LC4).
- **Why exclusion is problematic:** Verified by Peek (2018) as the primary descending driver of forward jump escapes (in response to looming from behind).
- **Decision Status:** `UNRESOLVED — REQUIRES USER APPROVAL: Should DNp11 be added as the forward escape readout?`

### 3. DNg40 (Rank 5, 3,978 visual synapses, ~20.0% visual share)
- **Status:** EXCLUDED from Circuit v1.
- **Why it was excluded:** `EVIDENCE: UNVERIFIED` for escape behavior. Connectomically robust (survives $w_{\min}=10$ on both sides with dual convergence), but predicted glutamatergic and lacks physiological verification.
- **Decision Status:** `UNRESOLVED — REQUIRES USER APPROVAL: Should DNg40 remain excluded until experimental behavioral evidence emerges?`

### 4. DNp103 (Rank 3, 5,400 visual synapses, ~9.6% visual share)
- **Status:** EXCLUDED from Circuit v1.
- **Why it was excluded:** `EVIDENCE: UNVERIFIED` for escape behavior. Strongly LPLC2-dominated (5,065 LPLC2 vs. 335 LC4) with lower visual share due to an enormous dendritic tree.
- **Decision Status:** `UNRESOLVED — REQUIRES USER APPROVAL: Should DNp103 remain excluded?`

---

## 4. Excluded Intermediate Pathways (Interneurons)

In Phase 3, an unverified "Interneuron Inclusion Rule" was asserted:
> *"No interneurons are included in Circuit v1."*

Phase 2 analysis proves that two-step pathways carry massive visual traffic:
1. **PVLP010 (glutamate):** Receives 1,257 visual synapses and delivers 1,710 synapses to 30 candidate DNs ($\text{PathScore} = 2.15 \times 10^6$).
2. **LHAD1g1 (GABA):** Receives 1,308 visual synapses and delivers 1,556 synapses to 26 candidate DNs ($\text{PathScore} = 2.04 \times 10^6$).
3. **PVLP151 (acetylcholine):** Receives 2,530 visual synapses and delivers 645 synapses to 23 candidate DNs ($\text{PathScore} = 1.63 \times 10^6$).
4. **PVLP122 (acetylcholine):** Receives 1,503 visual synapses and delivers 1,003 synapses to 25 candidate DNs ($\text{PathScore} = 1.51 \times 10^6$).

**Epistemic Finding:** Excluding these interneurons is a legitimate *computational modeling simplification* for a feedforward Circuit v1, but it is NOT a biological finding. It must be explicitly recognized as an engineering assumption, not a connectomic truth.
