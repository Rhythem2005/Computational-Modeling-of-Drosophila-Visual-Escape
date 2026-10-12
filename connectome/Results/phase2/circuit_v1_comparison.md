# Phase 2: Circuit v1 Evaluation & Connectomic Comparison

**Phase:** Phase 2  
**Status:** COMPLETE  
**Date:** 2026-09-22  
**Evaluation Target:** Provisional Phase 3 Circuit v1 ({LC4, LPLC2, DNp01, DNp04, DNp06})  
**Dataset:** Drosophila MaleCNS v1.0  

---

## 1. Executive Summary

Phase 3 constructed a provisional, frozen Circuit v1 containing 317 neurons and 11,286 edges based on the neuron types {LC4, LPLC2, DNp01, DNp04, DNp06}. However, its biological membership decisions lacked a documented Phase 2 analysis and relied on an unverified assertion that "no interneurons are included" and "other DNs were not promoted in Phase 2."

This Phase 2 evaluation establishes that:
1. **LC4 and LPLC2** are definitively supported as the primary visual input populations for looming detection (Klapoetke et al. 2017; von Reyn et al. 2014).
2. **DNp01 (Giant Fiber)** is definitively supported as the canonical short-mode escape trigger (Tanouye & Wyman 1980; von Reyn et al. 2014), exhibiting robust dual convergence (6,424 and 4,800 synapses; ~25.8% visual share across both bilateral pairs; >98% synapse retention at $w_{\min}=10$).
3. **DNp04** is definitively supported connectomically and biologically as an escape readout: it ranks #1 in the entire connectome for direct visual input (14,995 total synapses), has an unparalleled visual share (~67–70%), and is experimentally verified to drive backward escape takeoff in concert with DNp02 (Peek 2018; Dombrovski et al. 2023 *Nature*).
4. **DNp06** is biologically verified as a flight evasive steering channel (Kim, Park, Lee, & Kim 2023 *Curr Biol*), but connectomically it is substantially weaker and more diluted than previously assumed: it ranks #7 in visual input (2,871 synapses), has a low visual share (~6.3–6.8%), and loses over 35% of its visual synapses at $w_{\min}=10$. Four excluded DN types (DNp103, DNp02, DNg40, DNp11) receive significantly higher visual input than DNp06.
5. **Circuit v1 is connectomically incomplete without DNp02**: DNp02 is the obligate partner of DNp04 in executing backward takeoff (Peek 2018), has 4,214 visual synapses, and possesses a ~23% visual share. Excluding DNp02 solely because it is monospecifically tuned to LC4 rather than receiving dual LPLC2 input is an artificial modeling filter that fractures a verified biological synergy.

---

## 2. Component-by-Component Evaluation

### 2.1 Presynaptic Input Population: LC4
- **Phase 1 Discovery Support:** 126 neurons (63L, 63R). Identified as primary looming-sensitive projection neuron from lobula to optic glomeruli.
- **Phase 2 Quantitative Support:** 33,190 total direct synapses onto descending neurons across 1,429 edges ($w \ge 1$). Provides massive inputs to DNp04 (11,597 syn), DNp01 (6,362 syn), DNp02 (4,209 syn), DNp11 (3,666 syn), and DNp03 (2,507 syn).
- **Threshold Robustness:** 100% of LC4 neurons remain active at $w_{\min}=10$. Direct synapses are highly concentrated: 98% of LC4 synapses onto DNp04 and DNp01 survive $w_{\min}=10$.
- **Biological Evidence:** Strongly established looming velocity detector (von Reyn et al. 2014, 2017).
- **Unresolved Issues:** None.
- **Verdict:** **`SUPPORTED`**

### 2.2 Presynaptic Input Population: LPLC2
- **Phase 2 Quantitative Support:** 185 neurons (92L, 93R). 24,519 total direct synapses onto descending neurons across 2,182 edges ($w \ge 1$). Provides massive inputs to DNp103 (5,065 syn), DNp01 (4,862 syn), DNp04 (3,398 syn), DNg40 (2,998 syn), and DNp06 (1,719 syn).
- **Threshold Robustness:** 100% of LPLC2 neurons remain active at $w_{\min}=10$. Direct synapses to DNp01 and DNp04 survive at >95% rate.
- **Biological Evidence:** Strongly established looming size / radial expansion detector (Klapoetke et al. 2017; Ache et al. 2019).
- **Unresolved Issues:** None.
- **Verdict:** **`SUPPORTED`**

### 2.3 Primary Readout: DNp01 (Giant Fiber)
- **Phase 1 Discovery Support:** Pre-selected in Phase 0; identified in Phase 1 as receiving 11,224 direct visual synapses with strong bilateral convergence.
- **Phase 2 Quantitative Support:**
  - Left (10010): 3,782 LC4 + 2,642 LPLC2 = 6,424 visual synapses; total incoming = 24,896; **visual share = 25.80%**.
  - Right (10001): 2,580 LC4 + 2,220 LPLC2 = 4,800 visual synapses; total incoming = 18,582; **visual share = 25.83%**.
  - Remarkable bilateral symmetry in visual share (~25.8%).
- **Threshold Robustness:**
  - At $w_{\min}=1$: 11,224 synapses.
  - At $w_{\min}=3$: 11,220 synapses (99.96% retention).
  - At $w_{\min}=10$: 11,072 synapses (98.65% retention).
  - Extremely robust across all thresholds; virtually impervious to noise filtering.
- **Biological Evidence:** Definitive gold standard. Mediates short-mode unsteered escape takeoff (Tanouye & Wyman 1980; Allen et al. 2006; von Reyn et al. 2014).
- **Unresolved Issues:** Low classifier confidence for predicted ACh (0.50–0.56), consistent with known mixed electrical (gap junction via innexin shakB) and chemical transmission at GF terminals.
- **Verdict:** **`SUPPORTED`**

### 2.4 Readout: DNp04
- **Phase 1 Discovery Support:** Discovered in Phase 1 as the top-ranking descending neuron by total visual input (14,995 synapses). Promoted to Circuit v1.
- **Phase 2 Quantitative Support:**
  - Left (531898): 6,811 LC4 + 1,957 LPLC2 = 8,768 visual synapses; total incoming = 12,604; **visual share = 69.57%**.
  - Right (11137): 4,786 LC4 + 1,441 LPLC2 = 6,227 visual synapses; total incoming = 9,326; **visual share = 66.77%**.
  - Ranks #1 in the entire connectome for both absolute visual weight and connectomic specificity (over 2/3 of all its inputs come from LC4 and LPLC2).
- **Threshold Robustness:**
  - At $w_{\min}=1$: 14,995 synapses.
  - At $w_{\min}=3$: 14,985 synapses (99.93% retention).
  - At $w_{\min}=10$: 14,665 synapses (97.80% retention).
  - Both bilateral pairs survive $w_{\min}=10$ with massive edge weights (mean edge weight ~55).
- **Biological Evidence:** Verified non-GF escape takeoff steering neuron. Widespread dendritic arborization covers the entire LC4 glomerulus (Namiki et al. 2018); co-activation with DNp02 drives backward takeoff (Peek 2018; Dombrovski et al. 2023 *Nature*).
- **Unresolved Issues:** Biological takeoff execution requires co-activation with DNp02, which is currently excluded from Circuit v1.
- **Verdict:** **`SUPPORTED`**

### 2.5 Readout: DNp06
- **Phase 1 Discovery Support:** Pre-selected in Phase 0 config. Ranked #7 in Phase 1 discovery (2,871 visual synapses).
- **Phase 2 Quantitative Support:**
  - Left (10228): 705 LC4 + 886 LPLC2 = 1,591 visual synapses; total incoming = 23,365; **visual share = 6.81%**.
  - Right (10584): 447 LC4 + 833 LPLC2 = 1,280 visual synapses; total incoming = 20,242; **visual share = 6.32%**.
  - Connectomic visual share is relatively modest (~6.5%); over 93% of its input originates from non-visual pathways.
  - Ranks lower in absolute visual weight than four excluded DN types (DNp103: 5,400 syn; DNp02: 4,214 syn; DNg40: 3,978 syn; DNp11: 3,737 syn).
- **Threshold Robustness:**
  - At $w_{\min}=1$: 2,871 synapses.
  - At $w_{\min}=3$: 2,831 synapses (98.61% retention).
  - At $w_{\min}=10$: 1,878 synapses (65.41% retention).
  - Drops 34.6% of its visual synapses when moving from $w_{\min}=1$ to $w_{\min}=10$. While both bilateral pairs survive $w_{\min}=10$, individual connection weights are substantially more dispersed.
- **Biological Evidence:** Directly verified in published literature (Kim, Park, Lee, & Kim 2023 *Current Biology*) as mediating evasive flight steering turns in response to looming and moving visual stimuli.
- **Unresolved Issues:** Inclusion in Circuit v1 was historically driven by Phase 0 selection rather than connectomic ranking. However, because its flight evasive function is experimentally demonstrated, its inclusion is biologically defensible as a distinct motor modality (flight steering vs. leg takeoff).
- **Verdict:** **`POSSIBLE (Biologically Supported, Connectomically Diluted)`**

---

## 3. High-Impact Candidates Excluded from Circuit v1

| Excluded Type | Visual Weight ($w_1$) | Visual Share | LC4 / LPLC2 Convergence | Verified Biological Role | Risk / Impact of Exclusion |
|---|---|---|---|---|---|
| **DNp02** | 4,214 synapses (#4 in connectome) | 23.00% | LC4-monospecific (4,209 LC4 vs. 5 LPLC2; 0 LPLC2 at $w_{10}$) | Co-activated with DNp04 to execute backward jump takeoffs (Peek 2018; Dombrovski et al. 2023). | **CRITICAL:** DNp04 and DNp02 form a documented functional pair. Modeling DNp04 without DNp02 models only half of the backward escape circuit. |
| **DNp11** | 3,737 synapses (#6 in connectome) | 15.40% | Strongly LC4-dominated (3,666 LC4 vs. 71 LPLC2) | Primary driver of forward jump escapes (Peek 2018; Dombrovski et al. 2023). | **HIGH:** Excludes the forward escape trajectory, leaving Circuit v1 unable to model forward takeoffs. |
| **DNg40** | 3,978 synapses (#5 in connectome) | 19.98% | Balanced dual convergence (980 LC4 + 2,998 LPLC2) | `EVIDENCE: UNVERIFIED` for escape behavior; predicted glutamatergic. | **MODERATE:** Strong connectomic candidate, but lacks behavioral validation. |
| **DNp103** | 5,400 synapses (#3 in connectome) | 9.57% | LPLC2-dominated (335 LC4 + 5,065 LPLC2) | `EVIDENCE: UNVERIFIED` for escape behavior. | **MODERATE:** Substantial visual input, but low visual share due to ~28k total synapses. |

---

## 4. Synthesis and Scientific Recommendations

1. **Current Circuit v1 is computationally functional and provides a valid baseline for Phase 4**, but its readouts should be explicitly labeled:
   - **DNp01:** Canonical Short-Mode Escape Trigger
   - **DNp04:** Directional Takeoff Integration Channel
   - **DNp06:** Evasive Flight Steering Channel
2. **Circuit v1 should NOT be claimed as the complete or sole escape circuit**:
   - Omitting DNp02 means backward takeoff steering is incomplete.
   - Omitting DNp11 means forward takeoff steering is absent.
   - Omitting interneurons (PVLP122, LHAD1g1) assumes pure feedforward architecture.
3. **Formal Decision Recommendation for the User**:
   - **Option A (Preserve Frozen Circuit v1 Baseline):** Keep Circuit v1 as {LC4, LPLC2, DNp01, DNp04, DNp06}, documenting DNp02 and DNp11 as Phase 2 unresolved candidates deferred to Circuit v2.
   - **Option B (Expand Circuit v1 to Full Steering):** Formally include DNp02 and DNp11 to complete the documented directional takeoff repertoire (forward and backward jump control).
