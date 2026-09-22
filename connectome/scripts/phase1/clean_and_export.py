"""Phase 1 edge processing and matrix construction.

Filters raw edges by weight threshold, aggregates duplicate directed pairs,
and exports raw and normalized weight matrices.
"""

from pathlib import Path
import json
import numpy as np
import pandas as pd
import yaml

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent   # project root
CONFIG_PATH = ROOT_DIR / "config.yaml"

with open(CONFIG_PATH, "r") as f:
    cfg = yaml.safe_load(f)

WEIGHT_THRESHOLD = cfg["processing"]["weight_threshold"]
NORM_METHOD      = cfg["normalization"]["method"]

BASE_DIR = Path(__file__).resolve().parent.parent.parent   # connectome/
DATA_DIR = BASE_DIR / "data" / "phase1"

NODES_PATH = DATA_DIR / "nodes.csv"
EDGES_PATH = DATA_DIR / "raw_edges.csv"

if not NODES_PATH.exists() or not EDGES_PATH.exists():
    raise FileNotFoundError("Missing nodes.csv or raw_edges.csv. Run earlier steps first.")

nodes_df = pd.read_csv(NODES_PATH)
edges_df = pd.read_csv(EDGES_PATH)

print(f"Loaded {len(nodes_df)} nodes and {len(edges_df)} raw edges.")

# Filter edges below threshold
filtered_edges = edges_df[edges_df["weight"] >= WEIGHT_THRESHOLD].copy()
pruned_count = len(edges_df) - len(filtered_edges)
print(f"Filtered out {pruned_count} edges with weight < {WEIGHT_THRESHOLD}. "
      f"Remaining: {len(filtered_edges)}")

# Sum weights across duplicate directed pairs
pre_agg_count = len(filtered_edges)
pre_agg_pairs = filtered_edges.groupby(["bodyId_pre", "bodyId_post"]).ngroups

aggregated = (
    filtered_edges
    .groupby(["bodyId_pre", "bodyId_post"], as_index=False)
    .agg(
        weight=("weight", "sum"),
        # Preserve type/side metadata from first occurrence
        pre_type=("pre_type", "first"),
        pre_side=("pre_side", "first"),
        post_type=("post_type", "first"),
        post_side=("post_side", "first"),
    )
)

dup_pairs = pre_agg_count - len(aggregated)
print(f"Aggregated {dup_pairs} duplicate rows across {pre_agg_pairs} unique pairs → "
      f"{len(aggregated)} edges after aggregation.")

print("\n" + "=" * 50)
print("HEMISPHERIC INNERVATION ONTO DNp06 (Synapse Sums)")
print("=" * 50)
dnp06_inputs = aggregated[aggregated["post_type"] == "DNp06"]
if not dnp06_inputs.empty:
    innervation_table = dnp06_inputs.pivot_table(
        index=["pre_type", "pre_side"],
        columns=["post_side"],
        values="weight",
        aggfunc="sum",
        fill_value=0,
    )
    print(innervation_table)
else:
    print("  No inputs to DNp06 found in filtered edges.")

# Build N x N matrix: W[post_idx, pre_idx] = aggregated synapse count
# Structural weights are unsigned counts; neurotransmitter sign is stored as metadata.
node_ids = nodes_df["bodyId"].tolist()
n_nodes = len(node_ids)
id_to_idx = {body_id: idx for idx, body_id in enumerate(node_ids)}

W = np.zeros((n_nodes, n_nodes), dtype=np.float32)

for _, row in aggregated.iterrows():
    pre_idx  = id_to_idx.get(row["bodyId_pre"])
    post_idx = id_to_idx.get(row["bodyId_post"])
    if pre_idx is not None and post_idx is not None:
        W[post_idx, pre_idx] = row["weight"]

print("\n" + "=" * 50)
print("SELF-CONSISTENCY CHECK")
print("=" * 50)

mismatches = 0
for _, row in aggregated.iterrows():
    pre_idx  = id_to_idx.get(row["bodyId_pre"])
    post_idx = id_to_idx.get(row["bodyId_post"])
    if pre_idx is not None and post_idx is not None:
        matrix_val = W[post_idx, pre_idx]
        edge_val = row["weight"]
        if matrix_val != edge_val:
            mismatches += 1
            print(f"  MISMATCH: W[{post_idx},{pre_idx}] = {matrix_val}, "
                  f"expected {edge_val} (pre={row['bodyId_pre']}, post={row['bodyId_post']})")

assert mismatches == 0, f"{mismatches} matrix entries do not match aggregated edge weights!"
print(f"  ✓ All {len(aggregated)} matrix entries match aggregated edge weights.")

nonzero_matrix = np.count_nonzero(W)
edges_in_matrix = aggregated[
    aggregated["bodyId_pre"].isin(id_to_idx) & aggregated["bodyId_post"].isin(id_to_idx)
].shape[0]
assert nonzero_matrix == edges_in_matrix, (
    f"Nonzero matrix entries ({nonzero_matrix}) != edges in matrix ({edges_in_matrix})"
)
print(f"  ✓ Nonzero matrix entries ({nonzero_matrix}) == mapped edge count.")

w_max = W.max()
assert w_max > 0, "Maximum weight is zero — matrix is empty."

if NORM_METHOD == "max":
    W_norm = W / w_max
else:
    raise ValueError(f"Unknown normalization method: {NORM_METHOD}")

print(f"\n  Normalization: method={NORM_METHOD}, max_weight={w_max}")
print(f"  Normalized matrix range: [{W_norm.min():.6f}, {W_norm.max():.6f}]")

processed_edges_path = DATA_DIR / "processed_edges.csv"
matrix_raw_path      = DATA_DIR / "weight_matrix.npy"
matrix_norm_path     = DATA_DIR / "weight_matrix_normalized.npy"
index_map_path       = DATA_DIR / "matrix_index.json"

aggregated = aggregated[[
    "bodyId_pre", "pre_type", "pre_side",
    "bodyId_post", "post_type", "post_side",
    "weight",
]].sort_values(by="weight", ascending=False)

aggregated.to_csv(processed_edges_path, index=False)
np.save(matrix_raw_path, W)
np.save(matrix_norm_path, W_norm)

# Positional index to neuron metadata; predictedNt preserved as metadata
index_manifest = {}
for pos_idx, (_, row) in enumerate(nodes_df.iterrows()):
    index_manifest[pos_idx] = {
        "bodyId": int(row["bodyId"]),
        "type": row["type"],
        "side": row["side"],
        "predictedNt": row.get("predictedNt", "unknown"),
    }

with open(index_map_path, "w") as f:
    json.dump(index_manifest, f, indent=2)

print("\n" + "=" * 50)
print("PHASE 1 ARTIFACTS EXPORTED")
print("=" * 50)
print(f"1. Processed edges:      {processed_edges_path.relative_to(BASE_DIR.parent)}")
print(f"   Unique directed pairs: {len(aggregated)}")
print(f"   Total aggregated weight: {aggregated['weight'].sum()}")
print(f"2. Raw weight matrix:    {matrix_raw_path.relative_to(BASE_DIR.parent)} "
      f"(shape {W.shape})")
print(f"3. Normalized matrix:    {matrix_norm_path.relative_to(BASE_DIR.parent)} "
      f"(shape {W_norm.shape})")
print(f"4. Matrix index map:     {index_map_path.relative_to(BASE_DIR.parent)}")
print(f"5. Normalization method: {NORM_METHOD} (divisor = {w_max})")