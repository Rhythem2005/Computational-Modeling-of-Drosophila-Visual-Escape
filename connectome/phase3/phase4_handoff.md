# Phase 4 Handoff — Circuit v1 Contract

This document defines exactly what Phase 4 receives from Phase 3, what Phase 4 can and cannot change, and how to consume the frozen artifacts.

---

## 1. What Phase 4 Receives

### 1.1 Frozen Artifacts (in `connectome/phase3/`)

| File | Purpose | Frozen? |
|------|---------|---------|
| `circuit_v1_nodes.csv` | 317 neurons with metadata | **Yes — do not modify** |
| `circuit_v1_edges.csv` | 11,286 edges with weights | **Yes — do not modify** |
| `circuit_v1.json` | Complete circuit (nodes + edges + metadata) | **Yes — do not modify** |
| `circuit_v1_schema.json` | Schema definition | **Yes — do not modify** |
| `provenance.json` | Data provenance and checksums | **Yes — do not modify** |

### 1.2 How to Load

```python
import json
import pandas as pd

# Option A: Load CSV files separately
nodes = pd.read_csv("connectome/phase3/circuit_v1_nodes.csv")
edges = pd.read_csv("connectome/phase3/circuit_v1_edges.csv")

# Option B: Load complete circuit from JSON
with open("connectome/phase3/circuit_v1.json") as f:
    circuit = json.load(f)
    
nodes_list = circuit["nodes"]       # list of dicts
edges_list = circuit["edges"]       # list of dicts
params = circuit["parameters"]      # w_min, normalization, etc.
readouts = circuit["readout_summary"]  # per-DN input summary
```

### 1.3 Building the Weight Matrix

```python
import numpy as np

# Build node index
body_ids = nodes["bodyId"].tolist()
id_to_idx = {bid: i for i, bid in enumerate(body_ids)}
n = len(body_ids)

# Build W[post, pre] matrix (unsigned structural weights)
W = np.zeros((n, n), dtype=np.float64)
for _, row in edges.iterrows():
    i_pre = id_to_idx[row["bodyId_pre"]]
    i_post = id_to_idx[row["bodyId_post"]]
    W[i_post, i_pre] = row["weight"]

# Or use normalized weights
W_norm = np.zeros((n, n), dtype=np.float64)
for _, row in edges.iterrows():
    i_pre = id_to_idx[row["bodyId_pre"]]
    i_post = id_to_idx[row["bodyId_post"]]
    W_norm[i_post, i_pre] = row["weight_normalized"]
```

---

## 2. What Phase 4 CAN Do

Phase 4 is the simulation and modeling phase. It may:

| Action | Description |
|--------|-------------|
| **Assign synaptic signs** | Use `pre_nt` column to determine excitatory/inhibitory sign. All neurons are predicted ACh. Phase 4 decides the sign convention (e.g., +1 for acetylcholine). |
| **Scale weights** | Apply gain, conductance conversion, or other model-specific transforms to the frozen weights. |
| **Add activation functions** | Apply nonlinearities (ReLU, sigmoid, etc.) at each neuron. |
| **Set time constants** | Define leaky-integrator τ, simulation dt, etc. |
| **Define input encoding** | Choose how visual stimuli are encoded into LC4/LPLC2 activity. |
| **Read out from DNp01** | Use DNp01 activity as the primary escape trigger signal. |
| **Read out from DNp04/DNp06** | Use as secondary readouts for analysis. |
| **Apply spatial models** | If spatial processing is needed, use an explicit model (uniform, random, or ROI-proxy-based) with documentation. Do not claim retinotopic fidelity. |
| **Tune model parameters** | Adjust gain, threshold, time constants — NOT circuit structure. |
| **Add noise models** | Inject noise into simulation. |

---

## 3. What Phase 4 CANNOT Do

| Prohibition | Reason |
|-------------|--------|
| **Change neuron IDs** | Frozen connectome identity |
| **Add or remove neurons** | Circuit membership is frozen |
| **Change edge weights** | Connectome observation, not tunable parameter |
| **Add or remove edges** | Circuit topology is frozen |
| **Change neuron types** | Connectome annotation |
| **Change hemisphere assignments** | Connectome annotation |
| **Fabricate retinotopic mappings** | Not available in MaleCNS v1.0; must be explicitly modeled |
| **Change w_min threshold** | Frozen parameter (w_min=3) |
| **Reclassify readout roles** | DNp01=primary, DNp04/DNp06=secondary is frozen |
| **Use simulation results to change circuit** | Circuit is frozen before simulation |
| **Treat predicted NT as experimental** | Predictions, not functional assays |
| **Modify the frozen artifacts** | Any change requires a new circuit version |

---

## 4. Circuit Parameters Summary

| Parameter | Value | Phase 4 Can Change? |
|-----------|-------|-------------------|
| Node set | 317 neurons (5 types) | **No** |
| Edge set | 11,286 edges (w ≥ 3) | **No** |
| Raw weights | Unsigned synapse counts | **No** (but can scale/transform) |
| Normalized weights | weight / 172 | **No** (but can apply additional transforms) |
| Weight convention | W[post, pre] | **No** |
| Synaptic signs | Not applied (all predicted ACh) | **Phase 4 decides** |
| Activation function | Not defined | **Phase 4 decides** |
| Time constants | Not defined | **Phase 4 decides** |
| Input encoding | Not defined | **Phase 4 decides** |
| Retinotopy | NOT_AVAILABLE | **Phase 4 must model explicitly if needed** |
| Gain / conductance | Not defined | **Phase 4 decides** |

---

## 5. Readout Usage Guide

### 5.1 Primary Readout: DNp01 (Giant Fiber)

| Property | Value |
|----------|-------|
| Body IDs | 10010 (left), 10001 (right) |
| Total visual input | 11,220 synapses |
| LC4 input | 6,362 |
| LPLC2 input | 4,858 |
| Role | Escape trigger — threshold DNp01 activity to detect escape decision |

### 5.2 Secondary Readouts: DNp04, DNp06

| Property | DNp04 | DNp06 |
|----------|-------|-------|
| Body IDs | 531898 (L), 11137 (R) | 10228 (L), 10584 (R) |
| Total visual input | 14,985 | 2,831 |
| LC4 input | 11,597 | 1,142 |
| LPLC2 input | 3,388 | 1,689 |
| Role | Secondary readout for comparison/analysis | Secondary readout for comparison/analysis |

### 5.3 Inter-Readout Connectivity

There are 8 edges between readout neurons (total weight 88). The strongest is DNp04→DNp06 (ipsilateral, weights 31 and 23). Phase 4 should include these in the model — they are part of the frozen circuit topology.

---

## 6. Verification Before Phase 4

Before starting Phase 4 work, run:

```bash
python connectome/scripts/phase3/verify_circuit_v1.py
```

This re-verifies all frozen artifacts against source data. All 41 checks must pass. If any check fails (e.g., due to source data updates), **stop and investigate before proceeding.**

---

## 7. Creating Circuit v2

If Phase 4 discovers that Circuit v1 is insufficient (e.g., key pathways are missing), the correct procedure is:

1. Document the insufficiency with evidence
2. Return to Phase 2/3 to construct Circuit v2
3. Circuit v2 must go through the same freeze/verify process
4. Phase 4 must not retroactively modify Circuit v1

Circuit v1 remains the record of the first frozen circuit, even if superseded.
