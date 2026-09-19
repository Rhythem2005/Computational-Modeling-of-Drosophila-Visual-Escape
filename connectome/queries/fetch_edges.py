import os
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from neuprint import Client, fetch_adjacencies, NeuronCriteria as NC

# 1. Setup paths and load environment variables
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
NODES_PATH = DATA_DIR / "nodes.csv"

if not NODES_PATH.exists():
    raise FileNotFoundError(f"Missing {NODES_PATH}. Run fetch_nodes.py first.")

ENV_PATH = BASE_DIR.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

AUTH_TOKEN = os.getenv("NEUPRINT_TOKEN")
if not AUTH_TOKEN:
    raise ValueError("NEUPRINT_TOKEN not found in .env.")

# 2. Connect to MaleCNS
client = Client(
    server="https://neuprint.janelia.org",
    dataset="male-cns:v1.0",
    token=AUTH_TOKEN
)

# 3. Load extracted nodes
nodes_df = pd.read_csv(NODES_PATH)
body_ids = nodes_df["bodyId"].tolist()

print(f"Querying synaptic edges among {len(body_ids)} target neurons...")

# 4. Fetch directed edges (pre -> post)
criteria = NC(bodyId=body_ids)
_, conn_df = fetch_adjacencies(criteria, criteria)

if conn_df.empty:
    raise RuntimeError("No connections found among the specified target neurons.")

# 5. Annotate edges with type and side metadata for verification
node_meta = nodes_df.set_index("bodyId")[["type", "side"]]

conn_df = conn_df.merge(
    node_meta.rename(columns={"type": "pre_type", "side": "pre_side"}),
    left_on="bodyId_pre",
    right_index=True,
    how="left"
)

conn_df = conn_df.merge(
    node_meta.rename(columns={"type": "post_type", "side": "post_side"}),
    left_on="bodyId_post",
    right_index=True,
    how="left"
)

# Standardize columns and sort
conn_df = conn_df[[
    "bodyId_pre", "pre_type", "pre_side",
    "bodyId_post", "post_type", "post_side",
    "weight"
]].sort_values(by="weight", ascending=False)

# 6. Save artifact
output_path = DATA_DIR / "raw_edges.csv"
conn_df.to_csv(output_path, index=False)

# 7. Print circuit summary
print("\n" + "="*45)
print("SYNAPSE EXTRACTION COMPLETE")
print("="*45)
print(f"Total directed edges: {len(conn_df)}")
print(f"Total synapse count:  {conn_df['weight'].sum()}")
print("\nConnectivity Matrix (Edge counts by Type):")
type_summary = conn_df.pivot_table(
    index="pre_type",
    columns="post_type",
    values="weight",
    aggfunc=["count", "sum"],
    fill_value=0
)
print(type_summary)
print(f"\nArtifact saved to: {output_path.relative_to(BASE_DIR.parent)}")