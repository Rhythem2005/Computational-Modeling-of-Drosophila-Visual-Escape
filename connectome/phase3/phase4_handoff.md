# Phase 4 Handoff — Circuit v2 Contract (Active)

**Circuit ID:** `circuit_v2`
**Circuit Version:** `2.0.0`
**Status:** FROZEN & INDEPENDENTLY AUDITED
**Date:** 2026-09-22
**Source Dataset:** MaleCNS v1.0 (`male-cns:v1.0`)
**Archival Baseline:** `circuit_v1` (retained unchanged in `connectome/phase3/circuit_v1_*`)

---

## 1. Executive Summary & Active Contract

This document establishes the binding, non-negotiable contract between Phase 3 (Connectome Extraction & Refreeze) and Phase 4 (Biophysical Simulation & Behavioral Modeling).

**The active circuit for all Phase 4 modeling is Circuit v2.** Circuit v1 remains preserved as an archival baseline. Phase 4 must consume Circuit v2 exactly as frozen.

### 1.1 Scope Definition
Circuit v2 is formally designated as an:
> **"Expanded Biologically Motivated Direct Feedforward Sensorimotor Model Circuit"**

It captures direct monosynaptic sensorimotor integration from looming-sensitive visual projection neurons ({LC4, LPLC2}) to five biologically supported descending neuron channels ({DNp01, DNp04, DNp06, DNp02, DNp11}).

### 1.2 Quantitative Contract Summary

| Metric | Frozen Contract Value | Immutability |
|---|---|---|
| **Total Neurons** | **321** | FROZEN — No additions or deletions |
| **Visual Projection Neurons** | **311** (126 LC4, 185 LPLC2) | FROZEN |
| **Descending Readout Neurons** | **10** (5 bilateral pairs: DNp01, DNp04, DNp06, DNp02, DNp11) | FROZEN |
| **LC4 Population** | 126 neurons: **71 Left, 55 Right** | FROZEN (exact raw MaleCNS v1.0 counts) |
| **LPLC2 Population** | 185 neurons: **94 Left, 91 Right** | FROZEN (exact raw MaleCNS v1.0 counts) |
| **Total Directed Edges** | **11,557** ($w \ge 3$) | FROZEN — No edge additions or pruning |
| **Total Synaptic Weight** | **91,023** synapses | FROZEN |
| **Max Synaptic Weight** | **172** (intra-LPLC2 connection) | FROZEN divisor |
| **Linear Normalization** | $W_{\text{norm}} = W / 172 \in [0.0174, 1.0000]$ | FROZEN |
| **Weight Matrix Convention** | $W[\text{post}, \text{pre}]$ (row = postsynaptic, column = presynaptic) | FROZEN convention |
| **Weight Sign** | Unsigned structural synapse counts | FROZEN — signs must NOT be baked into weights |
| **Predicted Neurotransmitter** | Acetylcholine (metadata only, classifier confidence 0.84–0.99) | METADATA ONLY |
| **Retinotopy** | `RETINOTOPY = NOT_AVAILABLE` | FROZEN — soma coordinates $\neq$ receptive fields |

---

## 2. Frozen Machine-Readable Artifacts

All Circuit v2 artifacts are located in `connectome/phase3/`:

| Artifact File | Format | Contents & Verification |
|---|---|---|
| `circuit_v2_nodes.csv` | CSV | 321 neurons (`bodyId`, `type`, `somaSide`, `population`, `role`, `pre_nt`, `nt_confidence`) |
| `circuit_v2_edges.csv` | CSV | 11,557 directed edges (`bodyId_pre`, `bodyId_post`, `weight`, `weight_normalized`, `edge_class`, `pre_type`, `post_type`, `pre_side`, `post_side`, `pre_nt`) |
| `circuit_v2.json` | JSON | Complete circuit graph, node/edge tables, parameters, and metadata |
| `circuit_v2_schema.json` | JSON | Strict JSON schema definitions for validation |
| `circuit_v2_provenance.json` | JSON | Provenance record, pinned SHA-256 source file checksums, environment state |
| `circuit_v2_build_validation.json`| JSON | Build-time validation test results (23/23 checks passed) |

### 2.1 Pinned Raw Source Checksums (SHA-256)
- `body-annotations-male-cns-v1.0-minconf-0.5.feather`:
  `2177e246113e4cfbf1e7772ec37c6da1955ff22e8063d0b1f833101f99a9a3b2`
- `connectome-weights-male-cns-v1.0-minconf-0.5.feather`:
  `e35da783d1c686b2b58b3b87cd6a403ae43bfcfba8bff28e08ef752c1a56afc1`
- `body-neurotransmitters-male-cns-v1.0.feather`:
  `95c9289220663abeb3409f3ad9e5a7f8a53f8093f5139d15502cd08da8879621`

---

## 3. Readout Channels & Biological Scope

Circuit v2 captures five descending neuron readouts (10 individual neurons), each corresponding to a biologically and experimentally verified escape motor channel:

| Readout | Body IDs | Hemisphere | Visual Synapses ($w \ge 3$) | Visual Share | Biological Escape Role | Primary Experimental Citation |
|---|---|---|---|---|---|---|
| **DNp01** | 10010 (L)<br/>10001 (R) | Bilateral pair | 11,220 syn (126 LC4, 182 LPLC2) | 25.8% | **Giant Fiber unsteered jump:** Direct monosynaptic drive to TTMn leg extensor motor giant. Initiates emergency startle takeoff. | Tanouye & Wyman (1980); von Reyn et al. (2014) |
| **DNp04** | 531898 (L)<br/>11137 (R) | Bilateral pair | 14,985 syn (126 LC4, 178 LPLC2) | 68.3% | **Non-GF takeoff steering:** Spans entire LC4 glomerulus; spatial gradients map threat position for takeoff direction. | Peek (2018); Dombrovski et al. (2023) |
| **DNp02** | 10197 (L)<br/>10117 (R) | Bilateral pair | 4,209 syn (125 LC4, 0 LPLC2) | 23.0% | **Synergistic takeoff partner:** Innervates ventral LC4 glomerulus; co-activated with DNp04 during backward-directed takeoff jumps. | Peek (2018); Dombrovski et al. (2023) |
| **DNp11** | 10259 (L)<br/>10106 (R) | Bilateral pair | 3,688 syn (116 LC4, 9 LPLC2) | 15.2% | **Forward takeoff jump:** Drives forward postural shift and leg extension during forward escape jumps triggered by rear threats. | Peek (2018); Dombrovski et al. (2023) |
| **DNp06** | 10228 (L)<br/>10584 (R) | Bilateral pair | 2,831 syn (119 LC4, 160 LPLC2) | 6.5% | **In-flight evasive steering:** Drives rapid unilateral wingbeat amplitude modulation and evasive turns during tethered flight. | Kim et al. (2023); Namiki et al. (2018) |

> [!NOTE]
> DNp04 body ID `531898` has 6 digits while its partner `11137` has 5 digits. This was independently cross-checked against raw `body-annotations-male-cns-v1.0-minconf-0.5.feather` and verified to be an authentic MaleCNS v1.0 identifier, not a transcription error.

---

## 4. How Phase 4 Consumes Circuit v2

### 4.1 Loading Artifacts & Constructing the $W[\text{post}, \text{pre}]$ Matrix

```python
import pandas as pd
import numpy as np
import json

# 1. Load node and edge tables
nodes_df = pd.read_csv("connectome/phase3/circuit_v2_nodes.csv")
edges_df = pd.read_csv("connectome/phase3/circuit_v2_edges.csv")

# 2. Build index mapping
body_ids = nodes_df["bodyId"].tolist()
n_nodes = len(body_ids)
id_to_idx = {bid: i for i, bid in enumerate(body_ids)}

# 3. Construct W[post, pre] matrix
# W[post, pre] corresponds to row=postsynaptic, col=presynaptic
W_raw = np.zeros((n_nodes, n_nodes), dtype=np.float64)
W_norm = np.zeros((n_nodes, n_nodes), dtype=np.float64)

for _, edge in edges_df.iterrows():
    col_pre = id_to_idx[edge["bodyId_pre"]]
    row_post = id_to_idx[edge["bodyId_post"]]
    W_raw[row_post, col_pre] = edge["weight"]
    W_norm[row_post, col_pre] = edge["weight_normalized"]

print(f"Loaded Circuit v2: {n_nodes} nodes, {edges_df.shape[0]} edges.")
print(f"Max weight in matrix: {W_raw.max()} (Normalization divisor: 172.0)")
```

### 4.2 Edge Class Breakdown ($w \ge 3$)

```
                   count    sum    mean
edge_class
visual_to_readout   1141  36933   32.37
intra_population    9994  51846    5.19
cross_visual         388   1806    4.65
inter_readout         27    416   15.41
readout_to_visual      7     22    3.14
---------------------------------------
Total Edges:       11557  91023    7.88
```

---

## 5. Epistemic Constraints & Omissions

To maintain scientific integrity, Phase 4 modeling must operate under the following explicit constraints:

### 5.1 Omissions from Circuit v2
1. **Local Interneurons Omitted:** Intermediate interneurons (PVLP010, LHAD1g1, PVLP151, PVLP122, etc.) discovered in Phase 2 are omitted from Circuit v2. While connectomic paths exist (4,540 intermediates, 23,601 two-step paths), these interneurons lack cell-specific in vivo electrophysiological calibration. Adding them would introduce unconstrained latent variables.
2. **Other Direct Visual DNs Omitted:** The remaining 58 direct visual descending neurons (e.g., DNp103, DNg40, DNp03, DNp05) are omitted due to lack of verified behavioral escape evidence.
3. **Non-Visual Sensory Convergence Omitted:** Haltere, antennal mechanosensory, and central complex inputs converging onto readouts (especially DNp06) are omitted.
4. **Thoracic Motor Circuitry Omitted:** Motor neurons in the ventral nerve cord (VNC), such as TTMn and wing motor units, are not part of the brain connectome.
5. **Detailed Biophysical Dynamics Omitted:** The connectome provides structural synaptic counts, not channel conductances, membrane capacitances, or reversal potentials.

### 5.2 Neurotransmitter Predictions as Metadata
- All 321 neurons are predicted cholinergic (ACh) by a machine learning classifier (Eckstein et al. 2024 / MaleCNS v1.0).
- This prediction is **metadata, not ground truth physiology**.
- Phase 4 simulation models must apply synaptic polarities (+1 for ACh) as explicit modeling assumptions during conductance scaling, not treat them as unassailable facts.

### 5.3 Retinotopy Unavailable
- True optic lobe column coordinates (`assignedOlHex1`, `assignedOlHex2`) are NULL in MaleCNS v1.0 for all 311 visual projection neurons.
- Soma centroids ($x, y, z$) reflect cell body clusters along the brain margin and do NOT correspond to visual receptive field positions.
- **Phase 4 Prohibition:** Do NOT convert soma coordinates into visual angles. Any visual spatial receptive field mapping in Phase 4 must be explicitly declared as a *synthetic modeling assumption*, not recovered connectome data.

---

## 6. Phase 4 Freedoms & Prohibitions

### 6.1 What Phase 4 CAN Define (Modeling Assumptions)
Every item in this list must be documented as a *modeling parameter*, not a connectome fact:
- **Synaptic Sign Convention:** Assigning $+1$ (excitatory) to predicted cholinergic synapses.
- **Conductance Scaling:** Converting structural synapse counts $W$ to maximal synaptic conductance $g_{\text{syn}} = g_0 \cdot W$.
- **Membrane Dynamics:** Defining differential equations (e.g., Leaky Integrate-and-Fire, conductance-based, or rate models) and time constants ($\tau_m, \tau_s$).
- **Activation Functions:** Selecting threshold functions, transfer curves, or spike-generation mechanisms.
- **Noise Injection:** Adding Gaussian membrane noise or stochastic vesicle release models.
- **Input Encoding Scheme:** Defining how 2D synthetic visual stimuli (looming dark discs) are projected into LC4 expansion velocity and LPLC2 angular size firing rates.
- **Motor Decoding / Action Controller:** Formulating threshold rules or vector decoders mapping DNp01, DNp04, DNp02, DNp11, and DNp06 activities into takeoffs, steering angles, or flight turns.

### 6.2 What Phase 4 CANNOT Change (Frozen Prohibitions)
- **NO Node Additions or Deletions:** Node set is strictly locked at 321 neurons.
- **NO Edge Additions or Deletions:** Edge set is strictly locked at 11,557 directed edges.
- **NO Weight Modifications:** Unsigned structural weights cannot be tuned, optimized, or altered by backpropagation or gradient descent.
- **NO Alteration of $w_{\min}$:** The threshold remains $w_{\min} = 3$.
- **NO Type or Side Alterations:** Cell classifications and hemisphere assignments are fixed.
- **NO Circular Justification:** Phase 4 behavioral or simulation performance must NEVER be used to retroactively justify or modify Phase 3 circuit membership.

---

## 7. Verification Gate Before Phase 4 Execution

Before executing any Phase 4 code, the modeling environment must run and pass the three verification scripts:

```bash
# 1. Verify frozen Circuit v2 (48 checks)
python connectome/scripts/phase3/verify_circuit_v2.py

# 2. Run independent raw audit verifier (reads directly from raw feather files)
python connectome/scripts/phase3/independent_audit_verifier.py

# 3. Verify archival baseline Circuit v1 (41 checks)
python connectome/scripts/phase3/verify_circuit_v1.py
```

All verification checks must pass with zero errors, zero warnings, and tolerance = 0.
