# Phase 2: Decision & Epistemic Record

**Phase:** Phase 2  
**Status:** COMPLETE (Evidence Layer Established; Binding Decisions Deferred to User)  
**Date:** 2026-09-22  
**Dataset:** Drosophila MaleCNS v1.0  

---

## 1. Epistemic Framework

To maintain scientific integrity and prevent conflating observations with engineering assumptions, every finding and proposal in Phase 2 is classified into one of four epistemic tiers:

- **Layer 1: Connectomic Facts (MaleCNS v1.0 Data):** Directly measured synapse counts, cell counts, body annotations, and reconstructed morphology.
- **Layer 2: Derived Quantitative Metrics:** Reproducibly computed quantities (e.g. `visual_share`, threshold survivability at $w_{\min} \in \{1, 3, 10\}$, two-step path scores).
- **Layer 3: Biological Literature Evidence:** Published experimental findings (electrophysiology, optogenetics, behavior) from external peer-reviewed literature with verified citations.
- **Layer 4: Epistemic Status for Circuit Membership:** Evidence-based status assigned to each candidate population:
  - **`SUPPORTED`**: Connectomic and biological literature evidence concordantly validate the neuron's role in visual escape.
  - **`POSSIBLE`**: Biological evidence supports functional relevance, but connectomic input is diluted, or connectomics is strong but behavioral evidence is indirect.
  - **`UNRESOLVED`**: Strong candidate data exists, but inclusion requires an explicit project scope or architecture decision from the user.
  - **`NOT SUPPORTED`**: Data or literature does not support participation in visual escape (e.g., noise-level inputs, non-escape functional classes).

---

## 2. Layer 1: Connectomic Facts (MaleCNS v1.0)

| Fact ID | Observation | Source / Verification |
|---|---|---|
| F-01 | LC4 population consists of 126 traced neurons (63 Left, 63 Right). | `body-annotations`, `type == 'LC4'` |
| F-02 | LPLC2 population consists of 185 traced neurons (92 Left, 93 Right). | `body-annotations`, `type == 'LPLC2'` |
| F-03 | Exactly 63 descending neurons receive direct synaptic input ($w \ge 1$) from LC4 and/or LPLC2. | Pinned `connectome-weights` feather |
| F-04 | Direct visual input to descending neurons comprises 3,611 aggregated edges totaling 57,709 synapses. | Pinned `connectome-weights` feather |
| F-05 | 37 descending neurons receive direct input from BOTH LC4 and LPLC2 at $w_{\min}=1$; 22 at $w_{\min}=3$; 12 at $w_{\min}=10$. | Direct connectivity aggregation |
| F-06 | Visual projection inputs to descending neurons are >99.9% ipsilateral (only 21 contralateral edges out of 3,611). | Spatial annotations (`somaSide`) |
| F-07 | 4 descending neurons in MaleCNS v1.0 have null/missing type annotations (bodies 11851, 13539, 13964, 55579); NONE receive direct LC4 or LPLC2 input. | `body-annotations` audit |
| F-08 | 100% of LC4 (126/126) and 100% of LPLC2 (185/185) neurons are predicted cholinergic (mean confidence > 0.95). | `body-neurotransmitters` feather |
| F-09 | True optic lobe retinotopic column coordinates (`assignedOlHex1`, `assignedOlHex2`) are NULL for all LC4 and LPLC2 neurons in MaleCNS v1.0. | `body-annotations` audit |

---

## 3. Layer 2: Derived Quantitative Metrics

| Metric ID | Derived Quantity | Computation Procedure | Result Summary |
|---|---|---|---|
| D-01 | **Visual Share ($w_{\min}=1$)** | $\frac{\text{LC4\_weight} + \text{LPLC2\_weight}}{\text{total\_incoming\_weight}}$ | DNp04: ~68.2%; DNp01: ~25.8%; DNp02: ~23.0%; DNg40: ~20.0%; DNp11: ~15.4%; DNp06: ~6.6%. |
| D-02 | **Threshold Robustness** | Evaluated at $w_{\min} \in \{1, 3, 10\}$ | 33 DNs survive $w_{\min}=10$; 16 survive $w_{\min}=3$ only; 14 are weak ($w_{\min}=1$ only). |
| D-03 | **Synapse Retention ($w_{10} / w_1$)** | $\frac{\text{weight}(w_{\min}=10)}{\text{weight}(w_{\min}=1)}$ | DNp01: 98.6%; DNp04: 97.8%; DNp02: 98.1%; DNp11: 93.5%; DNp06: 65.4%. |
| D-04 | **Two-Step Pathway Capacity** | $\min(W_{\text{vis}\to X}, W_{X\to\text{DN}})$ and $W_{\text{vis}\to X} \times W_{X\to\text{DN}}$ | Top intermediates: PVLP010 (Glu), LHAD1g1 (GABA), PVLP151 (ACh), PVLP122 (ACh). |

---

## 4. Layer 3: Biological Evidence Assessment

| Population | Verified Function in Literature | Evidence Strength | Escape Relevance | Key Citation |
|---|---|---|---|---|
| **LC4** | Looming angular velocity detector | Strong (in vivo imaging, patch clamp, optogenetics) | Sensory trigger for looming expansion speed | von Reyn et al. (2014) *Neuron* |
| **LPLC2** | Looming size detector via radial motion opponency | Strong (two-photon imaging, optogenetics) | Sensory trigger for approaching object size | Klapoetke et al. (2017) *Nature* |
| **DNp01** | Giant Fiber; short-mode emergency escape jump | Definitive (decades of electrophysiology & behavior) | Canonical startle escape command neuron | Tanouye & Wyman (1980) *J Neurophysiol* |
| **DNp04** | Non-GF takeoff; postural steering for backward takeoff | Strong (optogenetics, connectomics, behavior) | Directional takeoff steering channel | Peek (2018) *Ph.D. Diss.*; Dombrovski et al. (2023) *Nature* |
| **DNp06** | Evasive flight turns and steering maneuvers | Moderate to Strong (tethered flight optogenetics) | Threat-induced flight steering channel | Kim et al. (2023) *Curr Biol* |
| **DNp02** | Obligate co-factor with DNp04 for backward takeoff | Strong (optogenetics, connectomics) | Directional takeoff steering channel | Peek (2018); Dombrovski et al. (2023) *Nature* |
| **DNp11** | Postural steering for forward jump takeoff | Strong (optogenetics, behavior) | Directional takeoff steering channel | Peek (2018); Dombrovski et al. (2023) *Nature* |
| **DNg40** | Neck/tectulum descending projections; glutamatergic | Weak (anatomical/connectomic only) | `EVIDENCE: UNVERIFIED` for escape behavior | Namiki et al. (2018) *eLife* |
| **DNp103** | Posterior slope descending projections | Weak (anatomical/connectomic only) | `EVIDENCE: UNVERIFIED` for escape behavior | Namiki et al. (2018) *eLife* |

---

## 5. Candidate Epistemic Status Matrix

| Candidate Population | Epistemic Status | Connectomic Evidence | Biological Evidence | Action Required |
|---|---|---|---|---|
| **LC4** | **`SUPPORTED`** | 126 neurons, massive input to escape DNs | Looming velocity detector | Approved presynaptic input population. |
| **LPLC2** | **`SUPPORTED`** | 185 neurons, massive input to escape DNs | Looming size detector | Approved presynaptic input population. |
| **DNp01** | **`SUPPORTED`** | Rank #2 visual input (11,224 syn); 25.8% visual share; 98.6% $w_{10}$ retention | Canonical Giant Fiber | Approved primary readout. |
| **DNp04** | **`SUPPORTED`** | Rank #1 visual input (14,995 syn); 68.2% visual share; 97.8% $w_{10}$ retention | Verified backward takeoff | Approved directional takeoff readout. |
| **DNp06** | **`POSSIBLE`** | Rank #7 visual input (2,871 syn); 6.6% visual share; 65.4% $w_{10}$ retention | Verified evasive flight turns | Retained in provisional Circuit v1 as flight steering readout, but acknowledged as connectomically diluted. |
| **DNp02** | **`UNRESOLVED`** | Rank #4 visual input (4,214 syn); 23.0% visual share; LC4-monospecific | Obligate partner of DNp04 | **REQUIRES USER APPROVAL** to add to Circuit v1. |
| **DNp11** | **`UNRESOLVED`** | Rank #6 visual input (3,737 syn); 15.4% visual share; LC4-dominated | Verified forward jump readout | **REQUIRES USER APPROVAL** to add to Circuit v1. |
| **DNg40** | **`UNRESOLVED`** | Rank #5 visual input (3,978 syn); 20.0% visual share; dual convergence | `EVIDENCE: UNVERIFIED` for escape | **REQUIRES USER APPROVAL** to evaluate or defer. |
| **DNp103** | **`UNRESOLVED`** | Rank #3 visual input (5,400 syn); 9.6% visual share; LPLC2-dominated | `EVIDENCE: UNVERIFIED` for escape | **REQUIRES USER APPROVAL** to evaluate or defer. |
| **Interneurons (PVLP122, LHAD1g1, etc.)** | **`UNRESOLVED`** | Massive 2-step pathways ($\text{PathScore} > 2 \times 10^6$); broad convergence | Feedforward vs. intermediate architecture | **REQUIRES USER APPROVAL** to include or keep pure feedforward. |
| **Remaining 27 DN types** | **`NOT SUPPORTED`** | Low input (<350 syn), visual share <2.5%, or noise-level ($w < 3$) | No visual escape evidence | Excluded from Circuit v1. |

---

## 6. Unresolved Scientific Decisions for User Sign-Off

The following decisions CANNOT be made unilaterally by the agent and require explicit user instructions before modifying the frozen circuit:

1. **Decision 1: Takeoff Steering Completeness (DNp02 & DNp11):**
   - *Context:* DNp04 alone does not execute backward escape; literature establishes that DNp04 + DNp02 co-activation produces backward takeoff, while DNp11 produces forward takeoff.
   - *Question for User:* Should Circuit v1 remain restricted to {DNp01, DNp04, DNp06}, or should DNp02 (backward jump) and DNp11 (forward jump) be formally approved for Circuit v1?
2. **Decision 2: Interneuron Inclusion vs. Feedforward Purity:**
   - *Context:* Phase 3 assumed a strictly feedforward visual $\to$ DN circuit. However, connectomics reveals substantial intermediate traffic through cholinergic (PVLP122, PVLP151) and GABAergic (LHAD1g1, PVLP011) interneurons.
   - *Question for User:* Should Circuit v1 preserve its feedforward-only scope, deferring interneurons to Circuit v2?
3. **Decision 3: Status of DNp06:**
   - *Context:* DNp06 has lower visual input (2,871 syn) and visual share (~6.5%) than four excluded candidates, but possesses direct experimental verification for flight steering.
   - *Question for User:* Confirm that DNp06 is retained in Circuit v1 as a specialized flight evasive readout despite its lower connectomic specificity.
