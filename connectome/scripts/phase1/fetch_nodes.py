"""Fetch target neuron metadata from MaleCNS v1.0.

Queries neuPrint for configured neuron types, standardizes hemisphere annotations,
and exports nodes.csv.
"""

import os
from pathlib import Path

import pandas as pd
import yaml
from dotenv import load_dotenv
from neuprint import Client, fetch_neurons, NeuronCriteria as NC

BASE_DIR = Path(__file__).resolve().parent.parent.parent   # connectome/
ROOT_DIR = BASE_DIR.parent                                 # project root
DATA_DIR = BASE_DIR / "data" / "phase1"
DATA_DIR.mkdir(parents=True, exist_ok=True)

ENV_PATH = ROOT_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

AUTH_TOKEN = os.getenv("NEUPRINT_TOKEN")
if not AUTH_TOKEN:
    raise ValueError("NEUPRINT_TOKEN not found. Set it inside your root .env file.")

CONFIG_PATH = ROOT_DIR / "config.yaml"
with open(CONFIG_PATH, "r") as f:
    cfg = yaml.safe_load(f)

SERVER       = cfg["dataset"]["server"]
DATASET      = cfg["dataset"]["name"]
TARGET_TYPES = cfg["neuron_types"]

client = Client(
    server=SERVER,
    dataset=DATASET,
    token=AUTH_TOKEN
)

print(f"Fetching neurons of types: {TARGET_TYPES} from {DATASET}...")

criteria = NC(type=TARGET_TYPES)
neurons_df, _ = fetch_neurons(criteria)

if neurons_df.empty:
    raise RuntimeError("No neurons retrieved. Verify target type names and API permissions.")

# Infer hemisphere from instance name if side column is absent
if "side" not in neurons_df.columns:
    def infer_side(row):
        inst = str(row.get("instance", ""))
        if inst.endswith("_L") or "(L)" in inst:
            return "left"
        if inst.endswith("_R") or "(R)" in inst:
            return "right"
        return "unknown"
    neurons_df["side"] = neurons_df.apply(infer_side, axis=1)

desired_cols = ["bodyId", "type", "instance", "side", "predictedNt", "status"]
cols_to_keep = [col for col in desired_cols if col in neurons_df.columns]
clean_nodes_df = neurons_df[cols_to_keep].copy()

clean_nodes_df.sort_values(by=["type", "side", "bodyId"], inplace=True)
clean_nodes_df.reset_index(drop=True, inplace=True)

output_path = DATA_DIR / "nodes.csv"
clean_nodes_df.to_csv(output_path, index=False)

print("\n" + "=" * 40)
print("NODE EXTRACTION COMPLETE")
print("=" * 40)
print(f"Total target neurons saved: {len(clean_nodes_df)}")
print("\nNeuron counts by Type and Side:")
print(clean_nodes_df.groupby(["type", "side"]).size().unstack(fill_value=0))
print(f"\nArtifact saved to: {output_path.relative_to(ROOT_DIR)}")