import os
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from neuprint import Client, fetch_neurons, NeuronCriteria as NC

# 1. Setup paths and load environment variables
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

ENV_PATH = BASE_DIR.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

AUTH_TOKEN = os.getenv("NEUPRINT_TOKEN")
if not AUTH_TOKEN:
    raise ValueError("NEUPRINT_TOKEN not found. Set it inside your root .env file.")

# 2. Connect to MaleCNS
client = Client(
    server="https://neuprint.janelia.org",
    dataset="male-cns:v1.0",
    token=AUTH_TOKEN
)

# 3. Query target neuron types
TARGET_TYPES = ["LC4", "LPLC2", "DNp06"]
print(f"Fetching neurons of types: {TARGET_TYPES} from male-cns:v1.0...")

criteria = NC(type=TARGET_TYPES)
neurons_df, _ = fetch_neurons(criteria)

if neurons_df.empty:
    raise RuntimeError("No neurons retrieved. Verify target type names and API permissions.")

# 4. Standardize side/hemisphere information
# neuPrint may provide 'side' explicitly or encode it in 'instance' (e.g., 'DNp06_L')
if "side" not in neurons_df.columns:
    def infer_side(row):
        inst = str(row.get("instance", ""))
        if inst.endswith("_L") or "(L)" in inst:
            return "left"
        if inst.endswith("_R") or "(R)" in inst:
            return "right"
        return "unknown"
    neurons_df["side"] = neurons_df.apply(infer_side, axis=1)

# 5. Retain critical columns
desired_cols = ["bodyId", "type", "instance", "side", "predictedNt", "status"]
cols_to_keep = [col for col in desired_cols if col in neurons_df.columns]
clean_nodes_df = neurons_df[cols_to_keep].copy()

# Sort for deterministic output
clean_nodes_df.sort_values(by=["type", "side", "bodyId"], inplace=True)

# 6. Save artifact
output_path = DATA_DIR / "nodes.csv"
clean_nodes_df.to_csv(output_path, index=False)

# 7. Print summary metrics
print("\n" + "="*40)
print("NODE EXTRACTION COMPLETE")
print("="*40)
print(f"Total target neurons saved: {len(clean_nodes_df)}")
print("\nNeuron counts by Type and Side:")
print(clean_nodes_df.groupby(["type", "side"]).size().unstack(fill_value=0))
print(f"\nArtifact saved to: {output_path.relative_to(BASE_DIR.parent)}")