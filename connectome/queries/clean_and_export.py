from pathlib import Path
import json
import numpy as np
import pandas as pd

# 1. Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

NODES_PATH = DATA_DIR / "nodes.csv"
EDGES_PATH = DATA_DIR / "raw_edges.csv"

if not NODES_PATH.exists() or not EDGES_PATH.exists():
    raise FileNotFoundError("Missing nodes.csv or raw_edges.csv. Run earlier steps first.")

# 2. Load data
nodes_df = pd.read_csv(NODES_PATH)
edges_df = pd.read_csv(EDGES_PATH)

print(f"Loaded {len(nodes_df)} nodes and {len(edges_df)} raw edges.")

# 3. Noise filtering (Threshold: weight >= 3)
WEIGHT_THRESHOLD = 3
filtered_edges = edges_df[edges_df["weight"] >= WEIGHT_THRESHOLD].copy()
pruned_count = len(edges_df) - len(filtered_edges)
print(f"Filtered out {pruned_count} edges with weight < {WEIGHT_THRESHOLD}. Remaining: {len(filtered_edges)}")

# 4. Neurotransmitter sign assignment
# Acetylcholine -> +1 (Excitatory); GABA / Glutamate -> -1 (Inhibitory)
def resolve_sign(row):
    nt = str(row.get("predictedNt", "")).lower()
    if "gaba" in nt or "glutamate" in nt:
        return -1
    # LC4 and LPLC2 are primarily cholinergic projection neurons
    return 1

nodes_df["sign"] = nodes_df.apply(resolve_sign, axis=1)
sign_map = nodes_df.set_index("bodyId")["sign"].to_dict()

filtered_edges["pre_sign"] = filtered_edges["bodyId_pre"].map(sign_map).fillna(1).astype(int)
filtered_edges["signed_weight"] = filtered_edges["pre_sign"] * filtered_edges["weight"]

# 5. Hemispheric innervation check onto DNp06
print("\n" + "="*50)
print("HEMISPHERIC INNERVATION ONTO DNp06 (Synapse Sums)")
print("="*50)
dnp06_inputs = filtered_edges[filtered_edges["post_type"] == "DNp06"]
innervation_table = dnp06_inputs.pivot_table(
    index=["pre_type", "pre_side"],
    columns=["post_side"],
    values="weight",
    aggfunc="sum",
    fill_value=0
)
print(innervation_table)

# 6. Construct N x N Signed Adjacency Matrix
# W[i, j] = connection from j (col) to i (row)
node_ids = nodes_df["bodyId"].tolist()
n_nodes = len(node_ids)
id_to_idx = {body_id: idx for idx, body_id in enumerate(node_ids)}

weight_matrix = np.zeros((n_nodes, n_nodes), dtype=np.float32)

for _, row in filtered_edges.iterrows():
    pre_idx = id_to_idx.get(row["bodyId_pre"])
    post_idx = id_to_idx.get(row["bodyId_post"])
    if pre_idx is not None and post_idx is not None:
        # matrix entry: target (post) row, source (pre) column
        weight_matrix[post_idx, pre_idx] = row["signed_weight"]

# 7. Save outputs
processed_edges_path = DATA_DIR / "processed_edges.csv"
matrix_path = DATA_DIR / "weight_matrix.npy"
index_map_path = DATA_DIR / "matrix_index.json"

filtered_edges.to_csv(processed_edges_path, index=False)
np.save(matrix_path, weight_matrix)

# Metadata mapping each matrix row/column index
index_manifest = {
    idx: {
        "bodyId": int(row["bodyId"]),
        "type": row["type"],
        "side": row["side"],
        "sign": int(row["sign"])
    }
    for idx, row in nodes_df.iterrows()
}

with open(index_map_path, "w") as f:
    json.dump(index_manifest, f, indent=2)

print("\n" + "="*50)
print("PHASE 1 ARTIFACTS EXPORTED")
print("="*50)
print(f"1. Processed edges:  {processed_edges_path.relative_to(BASE_DIR.parent)}")
print(f"2. Weight matrix:    {matrix_path.relative_to(BASE_DIR.parent)} (shape {weight_matrix.shape})")
print(f"3. Matrix index map: {index_map_path.relative_to(BASE_DIR.parent)}")