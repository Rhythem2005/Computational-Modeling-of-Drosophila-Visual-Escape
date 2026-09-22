# Phase 3 Final Report: Circuit Scope Analysis & Refreeze

**Project:** FLY — Computational Modeling of Drosophila Visual Escape
**Phase:** Phase 3 (Circuit Scope Analysis and Refreeze)
**Status:** COMPLETE & INDEPENDENTLY VERIFIED
**Date:** 2026-09-22
**Dataset:** Drosophila MaleCNS v1.0 (`male-cns:v1.0`)
**Pinned Source Data Checksums:**
- Body Annotations: `2177e246113e4cfbf1e7772ec37c6da1955ff22e8063d0b1f833101f99a9a3b2`
- Connectome Weights: `e35da783d1c686b2b58b3b87cd6a403ae43bfcfba8bff28e08ef752c1a56afc1`
- Body Neurotransmitters: `95c9289220663abeb3409f3ad9e5a7f8a53f8093f5139d15502cd08da8879621`

---

## 1. Executive Summary & Epistemic Pipeline

Phase 3 defines the scientifically defensible circuit scope for Phase 4 simulation by rigorously synthesizing the verified connectomic and biological literature evidence established in Phase 2.

```
FULL CONNECTOME (MaleCNS v1.0: 211,577 bodies, 151.8M edges)
      ↓
PHASE 1 DISCOVERY (63 candidate direct DNs, 311 visual projection neurons, 61.9k two-step paths)
      ↓
PHASE 2 EVIDENCE (Quantified visual share, w1/w3/w10 threshold robustness, verified literature citations)
      ↓
PHASE 3 CIRCUIT DEFINITION (Scientific question scoping, non-ranked scope comparison, freeze & independent verification)
      ↓
PHASE 4 SIMULATION (Biophysical simulation of visual looming escape behavior — NOT STARTED)
```

Provisional Circuit v1 was not assumed to be final, nor was it arbitrarily expanded. By evaluating every candidate against connectomic metrics, threshold robustness, and verified biological evidence, Phase 3 establishes an explicit distinction between:
1. **Scope A (Minimal Direct Baseline — Circuit v1):** 317 neurons, 11,286 edges at $w_{\min}=3$. Strictly enforces dual visual convergence (both LC4 and LPLC2 at $w \ge 3$) and monosynaptic connectivity.
2. **Scope B (Expanded Biologically Motivated Direct Feedforward Model Circuit — Circuit v2):** 321 neurons, 11,557 edges at $w_{\min}=3$. Captures the biological motor synergy of takeoff steering by incorporating **DNp02** (synergistic takeoff partner of DNp04) and **DNp11** (forward takeoff jump readout) alongside **DNp01** (unsteered emergency jump) and **DNp06** (flight steering).
3. **Scope C (Multi-Stage Connectome Circuit):** Connectome-derived intermediate interneurons (PVLP010, LHAD1g1, PVLP151, PVLP122, etc.). Documented for future multi-stage modeling, but excluded from immediate feedforward simulation.

Both Circuit v1 and Circuit v2 are fully frozen, independently verified against the source connectome data (tolerance=0), and documented with complete provenance.

---

## 2. Critical Evaluation of Current Circuit v1

The provisional Circuit v1 contains five neuron populations: LC4, LPLC2, DNp01, DNp04, DNp06. Each component is evaluated below based exclusively on Phase 2 verified evidence:

| Neuron | Connectomic Support | Biological Evidence | Behavioral Relevance | Threshold Robustness | Phase 3 Status |
|---|---|---|---|---|---|
| **LC4** | 126 neurons (71L/55R); 100% cholinergic ($p > 0.95$); massive projections to DNp04, DNp01, DNp02, DNp11 | Direct in vivo 2-photon imaging, patch-clamp, optogenetics (von Reyn et al. 2014; 2017) | Encodes visual looming angular expansion velocity; dynamic trigger for escape | 100% of population identified; high-weight edges robust to $w_{\min}=10$ | **SUPPORTED** |
| **LPLC2** | 185 neurons (94L/91R); 100% cholinergic ($p > 0.95$); massive projections to DNp01, DNp04, DNp103, DNg40 | Direct 2-photon imaging & optogenetics (Klapoetke et al. 2017; Ache et al. 2019) | Computes radial motion opponency; encodes looming angular size; size threshold trigger | 100% of population identified; high-weight edges robust to $w_{\min}=10$ | **SUPPORTED** |
| **DNp01** | 2 neurons (1L/1R); Rank #2 visual input (11,224 syn); 25.8% visual share; balanced dual input (57% LC4, 43% LPLC2) | Decades of electrophysiology & genetics (Tanouye & Wyman 1980; Allen et al. 2006; von Reyn et al. 2014) | Giant Fiber; canonical command neuron triggering short-mode unsteered emergency escape jump | 98.6% synaptic retention at $w_{\min}=10$; highly stable bilateral symmetry | **SUPPORTED** |
| **DNp04** | 2 neurons (1L/1R); Rank #1 visual input (14,995 syn); 68.2% visual share (unmatched in CNS); dual convergence | Optogenetics, anatomical reconstruction, connectomics (Peek 2018; Dombrovski et al. 2023; Namiki et al. 2018) | Non-GF directional takeoff steering; co-activated with DNp02 to direct backward jump | 97.8% synaptic retention at $w_{\min}=10$; dendrites span entire LC4 glomerulus | **SUPPORTED** |
| **DNp06** | 2 neurons (1L/1R); Rank #7 visual input (2,871 syn); 6.6% visual share; dual convergence (LC4 40%, LPLC2 60%) | Optogenetic tethered-flight wingbeat physiology (Kim et al. 2023; Namiki et al. 2018) | Evasive flight turns and steering maneuvers during flight in response to looming visual threats | 98.6% retention at $w_3$, but drops to 65.4% at $w_{10}$; visual input diluted by large arbor | **SUPPORTED AS BASELINE** |

---

## 3. In-Depth Candidate Analyses

### 3.1 DNp01 (Giant Fiber) Analysis
- **Direct LC4 Input:** 6,362 synapses ($w_1$), 6,362 ($w_3$), 6,362 ($w_{10}$) [3,782 L / 2,580 R].
- **Direct LPLC2 Input:** 4,862 synapses ($w_1$), 4,858 ($w_3$), 4,710 ($w_{10}$) [2,642 L / 2,220 R].
- **Visual-Input Share:** 25.80% (L), 25.83% (R). Over one-quarter of its entire incoming synaptic budget across the entire brain originates directly from LC4 and LPLC2.
- **Threshold Robustness:** Extremely robust. 99.96% weight retention at $w_3$, 98.6% weight retention at $w_{10}$. Bilateral visual share is extraordinarily symmetric (~25.8% on both sides).
- **Biological Evidence:** Canonical command-like escape neuron in *Drosophila* (Tanouye & Wyman 1980 *J Neurophysiol*; von Reyn et al. 2014 *Neuron*).
- **Role as Potential Behavioral Readout:** Primary emergency escape jump trigger. Directly excites the motor giant (TTMn) via electrical synapses and the peripherally synapsing interneuron (PSI) via chemical synapses to activate the tergotrochanteral jump muscle and wing depressor muscles.
- **Limitations:** Drives stereotyped, unsteered "short-mode" escapes (jump without wing elevation). It does NOT mediate directional takeoff steering or long-mode escapes (which require preparatory postural adjustments).
- **Phase 3 Determination:** DNp01 must remain in the circuit as the primary emergency escape readout across all scopes.

### 3.2 DNp04 Analysis
- **Direct LC4 Input:** 11,597 synapses ($w_1$), 11,597 ($w_3$), 11,597 ($w_{10}$) [6,811 L / 4,786 R].
- **Direct LPLC2 Input:** 3,398 synapses ($w_1$), 3,388 ($w_3$), 3,068 ($w_{10}$) [1,957 L / 1,441 R].
- **Visual-Input Share:** **69.57%** (L), **66.77%** (R). The highest visual specificity of any descending neuron in the entire connectome; over two-thirds of its dendritic input is purely visual.
- **Threshold Robustness:** 99.93% retention at $w_3$, 97.8% retention at $w_{10}$.
- **Biological Evidence:** Peek (2018 *Ph.D. Diss.*, University of Chicago / Card Lab); Dombrovski, Peek, et al. (2023 *Nature*); Namiki et al. (2018 *eLife*). Morphologically unique: dendrites arborize across the entire LC4 optic glomerulus. Synaptic gradients across LC4 boutons map threat location into directional takeoff trajectories.
- **Relationship to Takeoff Circuitry:** Non-GF takeoff driver. Optogenetic activation demonstrates that DNp04 drives backward-directed postural adjustments.
- **Limitations:** Behavioral and physiological testing (Peek 2018; Dombrovski et al. 2023) indicates that DNp04 does not act as an isolated single-command switch for backward escape; it acts in synergistic co-activation with **DNp02** during backward takeoff.
- **Phase 3 Determination:** DNp04 must remain in the circuit as the primary non-GF directional takeoff channel.

### 3.3 DNp06 Analysis
- **Direct LC4 Input:** 1,152 synapses ($w_1$), 1,142 ($w_3$), 698 ($w_{10}$) [705 L / 447 R].
- **Direct LPLC2 Input:** 1,719 synapses ($w_1$), 1,689 ($w_3$), 1,180 ($w_{10}$) [886 L / 833 R].
- **Visual-Input Share:** **6.81%** (L), **6.32%** (R).
- **Threshold Robustness:** Retains 98.6% of weight at $w_3$, but drops to 65.4% at $w_{10}$, indicating a high proportion of moderate-weight synaptic connections.
- **Explicit Distinction:**
  - *Connectomic Support:* Moderate absolute input (2,871 synapses across bilateral pair), balanced dual convergence (~40% LC4, ~60% LPLC2). However, visual share is low (~6.6%) because >93% of its input originates from non-visual regions (flight motor centers, haltere/mechanosensory inputs, central complex).
  - *Biological Evidence:* Definitive for flight steering. Kim, Park, Lee, & Kim (2023 *Curr Biol*) demonstrated that DNp06 responds specifically to visual threats during tethered flight, and unilateral optogenetic stimulation drives rapid, coordinated evasive steering turns and wingbeat modulation. Axons terminate in the dorsal VNC tectulum (flight motor neuropil; Namiki et al. 2018).
  - *Modeling Convenience:* Provides a distinct behavioral modality (in-flight evasive steering) alongside terrestrial jump takeoffs (DNp01/DNp04), allowing the model to simulate both landed and flying threat reactions.
- **Phase 3 Determination:** DNp06 is retained as a specialized in-flight evasive readout. It is classified as `SUPPORTED AS BASELINE`, with explicit documentation that its connectomic visual share is diluted relative to takeoff channels.

### 3.4 DNp02 Analysis
- **Direct LC4 Input:** 4,209 synapses ($w_1$), 4,209 ($w_3$), 4,134 ($w_{10}$) [2,279 L / 1,930 R].
- **Direct LPLC2 Input:** 5 synapses ($w_1$), 0 ($w_3$), 0 ($w_{10}$).
- **Visual-Input Share:** **24.31%** (L), **21.69%** (R). Comparable to DNp01 (~25%).
- **Threshold Robustness:** 99.88% retention at $w_3$, 98.1% retention at $w_{10}$.
- **Biological Evidence:** Peek (2018); Dombrovski et al. (2023 *Nature*). Innervates the ventral compartment of the LC4 glomerulus. In vivo behavioral testing shows that DNp02 acts as a synergistic co-active partner with DNp04: simultaneous co-activation of DNp02 + DNp04 directs backward takeoff.
- **Direct vs. Intermediate Pathways:** While direct LPLC2 input is negligible ($w=0$ at $w \ge 3$), DNp02 participates in 515 two-step pathways receiving indirect LPLC2 signals via intermediate interneurons such as LHAD1g1 (PathProduct 56,968), PVLP130 (50,631), and PVLP076 (40,002).
- **Phase 3 Determination:** DNp02 is **SUPPORTED FOR INCLUSION IN EXPANDED CIRCUIT (Scope B / Circuit v2)**. Its exclusion from Circuit v1 was purely an artifact of enforcing strict direct dual convergence (0 direct LPLC2 synapses). Retaining DNp04 without DNp02 omits a key synergistic partner in takeoff steering.

### 3.5 DNp11 Analysis
- **Direct LC4 Input:** 3,666 synapses ($w_1$), 3,655 ($w_3$), 3,492 ($w_{10}$) [2,022 L / 1,644 R].
- **Direct LPLC2 Input:** 71 synapses ($w_1$), 33 ($w_3$), 0 ($w_{10}$) [56 L / 15 R].
- **Visual-Input Share:** **16.24%** (L), **14.55%** (R).
- **Threshold Robustness:** 98.7% retention at $w_3$, 93.5% retention at $w_{10}$.
- **Biological Evidence:** Peek (2018); Dombrovski et al. (2023 *Nature*). Innervates the LC4 glomerulus. Direct optogenetic and behavioral assays establish that DNp11 drives forward postural shifts and forward jump takeoff in response to looming threats approaching from the rear.
- **Suitability as Readout:** High-confidence readout for forward-directed escape jumps. Together with {DNp04, DNp02}, DNp11 expands the directional jump steering axis (forward vs. backward).
- **Phase 3 Determination:** DNp11 is **SUPPORTED FOR INCLUSION IN EXPANDED CIRCUIT (Scope B / Circuit v2)**.

### 3.6 Other Direct Visual DNs Reviewed
- **DNp103 (PVLP119):** Rank #3 by total visual input (5,400 syn, w1). Strongly LPLC2-dominated (5,065 LPLC2 vs. 335 LC4). Visual share is diluted (8.7% L, 10.5% R) across an enormous dendritic arbor (~28k total synapses). Lacks published physiological or behavioral escape validation (`EVIDENCE: UNVERIFIED`). Excluded from Scopes A and B.
- **DNg40 (hb5813056435):** Rank #5 by total visual input (3,978 syn, w1). Balanced dual convergence (980 LC4, 2,998 LPLC2), visual share ~20.0%, predicted glutamatergic ($p \approx 0.62$). Morphologically characterized projecting to neck/tectulum (Namiki et al. 2018), but lacks behavioral escape validation (`EVIDENCE: UNVERIFIED`). Excluded from Scopes A and B.
- **DNp03 & DNp05:** High LC4 input (>98% LC4; 2,508 and 1,342 syn respectively), but lack documented behavioral escape roles in external literature. Excluded.
- **DNpe056 & DNp71:** High LPLC2 input (>99% LPLC2; 1,626 and 1,197 syn respectively), but lack documented behavioral escape roles. Excluded.
- **DNp35 & DNpe025:** Moderate input, low visual share (<4% and <8%), weak threshold robustness at $w_{10}$. Excluded.

---

## 4. Intermediate Neurons Analysis

Phase 2 identified 4,540 intermediate interneurons participating in 23,601 two-step paths connecting LC4/LPLC2 to descending neurons.

### 4.1 Top Intermediate Populations
1. **PVLP010 (glutamate):** Receives 1,257 visual synapses (almost purely LC4); delivers 1,710 synapses across 30 DNs ($\text{PathScore} = 2.15 \times 10^6$).
2. **LHAD1g1 (GABA):** Receives 1,308 visual synapses (strongly LPLC2); delivers 1,556 synapses across 26 DNs ($\text{PathScore} = 2.04 \times 10^6$). Provides direct feedforward GABAergic input to DNp06 (453 syn L, 449 syn R) and DNp01 (414 syn L).
3. **PVLP151 (acetylcholine):** Receives 2,530 visual synapses (strongly LPLC2); delivers 645 synapses across 23 DNs ($\text{PathScore} = 1.63 \times 10^6$).
4. **PVLP011 (GABA):** Receives 7,400 visual synapses (purely LPLC2); delivers 205 synapses across 18 DNs ($\text{PathScore} = 1.52 \times 10^6$).
5. **PVLP122 (acetylcholine):** Receives 1,503 visual synapses (balanced); delivers 1,003 synapses across 25 DNs ($\text{PathScore} = 1.51 \times 10^6$).

### 4.2 Modeling Scope Comparison: Direct vs. Multi-Stage
- **Direct Visual $\to$ DN Scope (Scopes A & B):**
  - *Included:* LC4, LPLC2, and validated descending readouts.
  - *Excluded:* All 4,540 intermediate interneurons.
  - *Biological Rationale:* Focuses strictly on monosynaptic sensorimotor integration where sensory tuning (velocity vs. size) directly drives motor commands.
  - *Computational Consequences:* Clean, tractable dynamical model. Direct weight matrices without unmeasured latent states.
  - *Limitations:* Omits local feedforward inhibition (LHAD1g1, PVLP011) and glomerulus cross-talk that may sharpen temporal tuning in vivo.
- **Multi-Stage Connectome Scope (Scope C):**
  - *Included:* LC4, LPLC2, selected top interneurons (PVLP010, LHAD1g1, PVLP151, PVLP122), and descending readouts.
  - *Biological Rationale:* Incorporates feedforward excitation and lateral/feedforward inhibition in the optic glomeruli.
  - *Computational Consequences:* Introduces non-linear multi-stage dynamics.
  - *Limitations:* None of these individual interneurons have cell-specific in vivo electrophysiological or behavioral loss-of-function data in looming escape. Adding them to Phase 4 creates dozens of unconstrained free parameters (time constants, reversal potentials, non-linear activation thresholds) that cannot be calibrated against ground truth.

---

## 5. Defining the Scientific Question

The choice of circuit scope directly reflects the underlying scientific hypothesis:

### QUESTION A: Minimal Biologically Grounded Escape Controller
*Can a compact, connectome-derived direct visual-to-escape circuit produce functional, robust escape responses to looming threats?*
- **Required Scope:** Scope A (Circuit v1).
- **Focus:** Evaluates whether direct monosynaptic convergence from looming velocity detectors (LC4) and size detectors (LPLC2) onto canonical readouts (DNp01 for jump, DNp04 for takeoff, DNp06 for flight) is sufficient to execute threat detection and action selection.

### QUESTION B: Expanded Directional Escape Takeoff & Steering Controller
*Can a connectome-derived visual circuit execute expanded directional escape takeoff steering (forward vs. backward jumps) alongside emergency unsteered jumps and in-flight evasion?*
- **Required Scope:** Scope B (Circuit v2).
- **Focus:** Incorporates the documented motor synergies of the non-GF takeoff system ({DNp04, DNp02} for backward takeoff; {DNp11} for forward takeoff) established by Peek (2018) and Dombrovski et al. (2023).

---

## 6. Circuit Scope Options (Non-Ranked)

| Metric / Property | SCOPE A: Minimal Direct Baseline | SCOPE B: Expanded Biologically Motivated Direct Feedforward | SCOPE C: Multi-Stage Connectome |
|---|---|---|---|
| **Neuron Types** | LC4, LPLC2, DNp01, DNp04, DNp06 | LC4, LPLC2, DNp01, DNp04, DNp06, DNp02, DNp11 | LC4, LPLC2, Intermediates, DNs |
| **Total Neurons** | 317 | 321 | 350+ |
| **Edge Count ($w \ge 3$)** | 11,286 | 11,557 | >25,000 |
| **Inclusion Rule** | Strict dual visual convergence + direct input + verified escape | Direct visual input + verified escape steering / jump | Two-step pathway capacity + DN convergence |
| **Readout Channels** | 3 channels: DNp01 (jump), DNp04 (takeoff), DNp06 (flight turn) | 4 channels: DNp01 (emergency jump), DNp04+DNp02 (backward jump), DNp11 (forward jump), DNp06 (flight turn) | Multi-stage readouts with interneuron states |
| **Motor Synergy** | Incomplete backward synergy (DNp04 lacks DNp02); no forward jump | Expanded representation of verified directional jump channels | Full glomerulus network representation |
| **Parameter Uncertainty** | Very low (direct weights only) | Very low (direct weights only) | High (unmeasured interneuron dynamics) |

---

## 7. Modeling Principle: Completeness vs. Usefulness

Biological completeness must not be confused with experimental usefulness:
1. **Scope A (Circuit v1)** is a legitimate, rigorously controlled baseline model. It demonstrates the baseline performance of direct dual visual convergence.
2. **Scope B (Circuit v2)** captures the biological motor synergy of takeoff steering while maintaining pure feedforward tractability. It adds only 4 neurons (2 bilateral pairs) and 271 edges, providing an expanded directional takeoff representation.
3. **Scope C** represents high biological completeness in the brain, but introduces high parameter indeterminacy in simulation.

---

## 8. Final Circuit Decision & Formal Refreeze

### Circuit Version Status
- **Circuit v1 Retained as Archival Baseline:** Frozen in `connectome/phase3/circuit_v1_*`, 317 neurons, 11,286 edges. Verified (41/41 checks passed).
- **Circuit v2 Formally Frozen:** To support Question B (Expanded Directional Escape Steering), Circuit v2 has been deterministically extracted, frozen, and independently verified in `connectome/phase3/circuit_v2_*`.

### Circuit v2 Frozen Specifications
- **Total Neurons:** **321**
  - LC4: 126 (71 Left, 55 Right)
  - LPLC2: 185 (94 Left, 91 Right)
  - DNp01: 2 (10010 Left, 10001 Right)
  - DNp04: 2 (531898 Left, 11137 Right)
  - DNp06: 2 (10228 Left, 10584 Right)
  - DNp02: 2 (10197 Left, 10117 Right)
  - DNp11: 2 (10259 Left, 10106 Right)
- **Total Directed Edges ($w \ge 3$):** **11,557**
  - `visual_to_readout`: 1,141 edges (36,933 synapses)
  - `intra_population`: 9,994 edges (51,846 synapses)
  - `cross_visual`: 388 edges (1,806 synapses)
  - `inter_readout`: 27 edges (416 synapses)
  - `readout_to_visual`: 7 edges (22 synapses)
- **Total Synaptic Weight:** **91,023**
- **Max Weight:** 172
- **Threshold:** $w_{\min} = 3$
- **Normalization:** Max-normalization (`weight / 172`), range $[0, 1]$
- **Weight Matrix Convention:** $W[\text{post}, \text{pre}]$ (row = postsynaptic, column = presynaptic)
- **Synaptic Signs:** Unsigned structural weights. All 321 neurons are predicted cholinergic (acetylcholine, classifier confidence 0.84–0.99). Functional synaptic signs are NOT applied to frozen weights.
- **Retinotopy:** `RETINOTOPY = NOT_AVAILABLE`. MaleCNS v1.0 does not contain verified visual angle receptive field coordinates for LC4/LPLC2.
- **Intermediate Populations:** None (feedforward architecture).

---

## 9. Independent Validation Results

Circuit v2 was subjected to independent verification via `connectome/scripts/phase3/verify_circuit_v2.py`:
- **Checks Passed:** **48 / 48** (0 failures).
- **Neuron Identifiers:** 321/321 verified against source `body-annotations` feather.
- **Neuron Types & Sides:** 100% exact match against source annotations.
- **Edge Extraction:** Re-extracted from 1.05 GB `connectome-weights` feather with tolerance = 0; exactly 11,557 edges with zero weight discrepancies.
- **Integrity:** Zero duplicate edges, zero self-loops.
- **Provenance Checksums:** Exact SHA-256 match for all three source feather files.

---

## 10. Phase 4 Handoff Gate

Both Circuit v1 (Scope A baseline) and Circuit v2 (Scope B expanded directional circuit) are 100% frozen, machine-readable, and independently validated.

```
PHASE 4 CLEARED
```

Phase 3 is COMPLETE. Phase 4 simulation must NOT begin automatically until instructed.
