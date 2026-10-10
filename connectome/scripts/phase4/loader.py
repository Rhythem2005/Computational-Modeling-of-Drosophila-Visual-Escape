"""Circuit v2 loader for Phase 4 simulation.

Loads frozen Circuit v2 artifacts and constructs weight matrices.
Validates loaded data against the frozen contract.
Does NOT modify any Phase 3 files.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


# Phase 3 frozen artifact paths (relative to project root)
PHASE3_DIR = Path(__file__).resolve().parent.parent.parent / "phase3"

# Contract constants — used ONLY for validation checks, not in simulation dynamics
CONTRACT = {
    "n_neurons": 321,
    "n_edges": 11557,
    "total_synapses": 91023,
    "max_raw_weight": 172,
    "w_min": 3,
    "population_counts": {
        "LC4": 126,
        "LPLC2": 185,
        "DNp01": 2,
        "DNp04": 2,
        "DNp06": 2,
        "DNp02": 2,
        "DNp11": 2,
    },
    "hemisphere_counts": {
        "LC4": {"left": 71, "right": 55},
        "LPLC2": {"left": 94, "right": 91},
    },
    "dn_body_ids": {
        "DNp01": {"left": 10010, "right": 10001},
        "DNp04": {"left": 531898, "right": 11137},
        "DNp06": {"left": 10228, "right": 10584},
        "DNp02": {"left": 10197, "right": 10117},
        "DNp11": {"left": 10259, "right": 10106},
    },
}


def compute_sha256(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class CircuitData:
    """Container for loaded Circuit v2 data with validation."""

    def __init__(
        self,
        nodes_df: pd.DataFrame,
        edges_df: pd.DataFrame,
        body_ids: list[int],
        id_to_idx: dict[int, int],
        W_raw: np.ndarray,
        W_norm: np.ndarray,
        nt_map: dict[int, str],
        side_map: dict[int, str],
        type_map: dict[int, str],
        population_map: dict[int, str],
        file_hashes: dict[str, str],
    ):
        self.nodes_df = nodes_df
        self.edges_df = edges_df
        self.body_ids = body_ids
        self.id_to_idx = id_to_idx
        self.W_raw = W_raw
        self.W_norm = W_norm
        self.nt_map = nt_map
        self.side_map = side_map
        self.type_map = type_map
        self.population_map = population_map
        self.file_hashes = file_hashes

    @property
    def n_neurons(self) -> int:
        return len(self.body_ids)

    def get_population_indices(self, neuron_type: str, side: str | None = None) -> list[int]:
        """Get matrix indices for a population, optionally filtered by side."""
        indices = []
        for bid in self.body_ids:
            if self.type_map[bid] == neuron_type:
                if side is None or self.side_map[bid] == side:
                    indices.append(self.id_to_idx[bid])
        return indices

    def get_population_body_ids(self, neuron_type: str, side: str | None = None) -> list[int]:
        """Get bodyIds for a population, optionally filtered by side."""
        bids = []
        for bid in self.body_ids:
            if self.type_map[bid] == neuron_type:
                if side is None or self.side_map[bid] == side:
                    bids.append(bid)
        return bids

    def get_dn_index(self, dn_type: str, side: str) -> int:
        """Get matrix index for a specific DN neuron."""
        bid = CONTRACT["dn_body_ids"][dn_type][side]
        return self.id_to_idx[bid]

    def get_dn_body_id(self, dn_type: str, side: str) -> int:
        """Get bodyId for a specific DN neuron."""
        return CONTRACT["dn_body_ids"][dn_type][side]

    def get_input_indices(self) -> list[int]:
        """Get matrix indices for all input neurons (LC4 + LPLC2)."""
        return self.get_population_indices("LC4") + self.get_population_indices("LPLC2")

    def get_dn_indices(self) -> list[int]:
        """Get matrix indices for all DN neurons."""
        indices = []
        for dn_type in ["DNp01", "DNp04", "DNp06", "DNp02", "DNp11"]:
            indices.extend(self.get_population_indices(dn_type))
        return indices

    def describe_edge_types(self) -> dict[str, dict[str, int]]:
        """Break down edges by type: input->DN, input->input, DN-involving, etc."""
        result = {}
        for edge_class in self.edges_df["edge_class"].unique():
            sub = self.edges_df[self.edges_df["edge_class"] == edge_class]
            result[edge_class] = {
                "count": len(sub),
                "total_synapses": int(sub["weight"].sum()),
            }
        return result


def load_circuit(phase3_dir: Path | None = None) -> CircuitData:
    """Load frozen Circuit v2 and validate against contract.

    Raises ValueError if any validation check fails.
    """
    if phase3_dir is None:
        phase3_dir = PHASE3_DIR

    nodes_path = phase3_dir / "circuit_v2_nodes.csv"
    edges_path = phase3_dir / "circuit_v2_edges.csv"

    if not nodes_path.exists():
        raise FileNotFoundError(f"Missing: {nodes_path}")
    if not edges_path.exists():
        raise FileNotFoundError(f"Missing: {edges_path}")

    # Hash files BEFORE loading (immutability proof)
    file_hashes = {
        "circuit_v2_nodes.csv": compute_sha256(nodes_path),
        "circuit_v2_edges.csv": compute_sha256(edges_path),
    }
    for extra in ["circuit_v2.json", "circuit_v2_provenance.json",
                   "circuit_v2_schema.json", "circuit_v2_build_validation.json"]:
        p = phase3_dir / extra
        if p.exists():
            file_hashes[extra] = compute_sha256(p)

    # Load CSVs
    nodes_df = pd.read_csv(nodes_path)
    edges_df = pd.read_csv(edges_path)

    # --- Validation checks ---
    errors: list[str] = []

    required_node_columns = {"bodyId", "type", "side", "population", "predicted_nt"}
    required_edge_columns = {
        "bodyId_pre", "bodyId_post", "weight", "weight_normalized", "pre_nt", "edge_class"
    }
    missing_node_columns = sorted(required_node_columns - set(nodes_df.columns))
    missing_edge_columns = sorted(required_edge_columns - set(edges_df.columns))
    if missing_node_columns:
        errors.append(f"Missing node columns: {missing_node_columns}")
    if missing_edge_columns:
        errors.append(f"Missing edge columns: {missing_edge_columns}")
    if errors:
        raise ValueError(
            "Circuit v2 schema validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        )

    # Node count
    if len(nodes_df) != CONTRACT["n_neurons"]:
        errors.append(f"Expected {CONTRACT['n_neurons']} neurons, got {len(nodes_df)}")

    # Edge count
    if len(edges_df) != CONTRACT["n_edges"]:
        errors.append(f"Expected {CONTRACT['n_edges']} edges, got {len(edges_df)}")

    # Total synapses
    total_syn = int(edges_df["weight"].sum())
    if total_syn != CONTRACT["total_synapses"]:
        errors.append(f"Expected {CONTRACT['total_synapses']} total synapses, got {total_syn}")

    # Max weight
    max_w = int(edges_df["weight"].max())
    if max_w != CONTRACT["max_raw_weight"]:
        errors.append(f"Expected max weight {CONTRACT['max_raw_weight']}, got {max_w}")

    # Min weight >= w_min
    min_w = int(edges_df["weight"].min())
    if min_w < CONTRACT["w_min"]:
        errors.append(f"Min weight {min_w} < w_min {CONTRACT['w_min']}")

    # Population counts
    for ntype, expected in CONTRACT["population_counts"].items():
        actual = len(nodes_df[nodes_df["type"] == ntype])
        if actual != expected:
            errors.append(f"{ntype}: expected {expected}, got {actual}")

    # Hemisphere counts
    for ntype, sides in CONTRACT["hemisphere_counts"].items():
        for side, expected in sides.items():
            actual = len(nodes_df[(nodes_df["type"] == ntype) & (nodes_df["side"] == side)])
            if actual != expected:
                errors.append(f"{ntype} {side}: expected {expected}, got {actual}")

    # DN body IDs
    for dn_type, sides in CONTRACT["dn_body_ids"].items():
        for side, expected_bid in sides.items():
            matches = nodes_df[(nodes_df["type"] == dn_type) & (nodes_df["side"] == side)]
            if len(matches) != 1:
                errors.append(f"{dn_type} {side}: expected 1 node, got {len(matches)}")
            elif int(matches.iloc[0]["bodyId"]) != expected_bid:
                errors.append(f"{dn_type} {side}: expected bodyId {expected_bid}, got {int(matches.iloc[0]['bodyId'])}")

    # No duplicate edges
    dup_check = edges_df.groupby(["bodyId_pre", "bodyId_post"]).size()
    if (dup_check > 1).any():
        errors.append(f"Found {(dup_check > 1).sum()} duplicate (pre,post) edge pairs")

    # No self-loops
    self_loops = edges_df[edges_df["bodyId_pre"] == edges_df["bodyId_post"]]
    if len(self_loops) > 0:
        errors.append(f"Found {len(self_loops)} self-loops")

    # Unique body IDs
    if not nodes_df["bodyId"].is_unique:
        errors.append("Duplicate bodyIds in nodes")

    # Neurotransmitter metadata must be present
    if "predicted_nt" not in nodes_df.columns:
        errors.append("Missing predicted_nt column in nodes — STOP")
    elif nodes_df["predicted_nt"].isna().any():
        errors.append("Some neurons missing predicted_nt — STOP")

    if "pre_nt" not in edges_df.columns:
        errors.append("Missing pre_nt column in edges — STOP")

    node_ids = set(nodes_df["bodyId"].astype(int))
    missing_pre = set(edges_df["bodyId_pre"].astype(int)) - node_ids
    missing_post = set(edges_df["bodyId_post"].astype(int)) - node_ids
    if missing_pre:
        errors.append(f"{len(missing_pre)} presynaptic bodyIds are absent from nodes")
    if missing_post:
        errors.append(f"{len(missing_post)} postsynaptic bodyIds are absent from nodes")

    expected_norm = edges_df["weight"].to_numpy(dtype=float) / CONTRACT["max_raw_weight"]
    actual_norm = edges_df["weight_normalized"].to_numpy(dtype=float)
    if not np.all(np.isfinite(actual_norm)):
        errors.append("weight_normalized contains NaN or Inf")
    elif not np.allclose(actual_norm, expected_norm, rtol=0.0, atol=1e-12):
        max_diff = float(np.max(np.abs(actual_norm - expected_norm)))
        errors.append(f"weight_normalized is inconsistent with weight/172 (max diff {max_diff})")

    if not missing_pre and "pre_nt" in edges_df.columns and "predicted_nt" in nodes_df.columns:
        node_nt = nodes_df.set_index("bodyId")["predicted_nt"]
        expected_pre_nt = edges_df["bodyId_pre"].map(node_nt)
        nt_mismatch = expected_pre_nt.astype(str) != edges_df["pre_nt"].astype(str)
        if nt_mismatch.any():
            errors.append(f"{int(nt_mismatch.sum())} edge pre_nt values disagree with node metadata")

    if errors:
        raise ValueError(
            "Circuit v2 validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        )

    # Build index mapping
    body_ids = nodes_df["bodyId"].tolist()
    n_nodes = len(body_ids)
    id_to_idx = {bid: i for i, bid in enumerate(body_ids)}

    # Build lookup maps
    nt_map = dict(zip(nodes_df["bodyId"], nodes_df["predicted_nt"]))
    side_map = dict(zip(nodes_df["bodyId"], nodes_df["side"]))
    type_map = dict(zip(nodes_df["bodyId"], nodes_df["type"]))
    population_map = dict(zip(nodes_df["bodyId"], nodes_df["population"]))

    # Construct W[post, pre] matrix — raw and normalized
    W_raw = np.zeros((n_nodes, n_nodes), dtype=np.float64)
    W_norm = np.zeros((n_nodes, n_nodes), dtype=np.float64)

    for _, edge in edges_df.iterrows():
        col_pre = id_to_idx[edge["bodyId_pre"]]
        row_post = id_to_idx[edge["bodyId_post"]]
        W_raw[row_post, col_pre] = edge["weight"]
        W_norm[row_post, col_pre] = edge["weight_normalized"]

    # Verify matrix properties with explicit exceptions (assertions can be disabled).
    if W_raw.shape != (n_nodes, n_nodes):
        raise ValueError(f"W shape {W_raw.shape} != ({n_nodes}, {n_nodes})")
    if np.count_nonzero(W_raw) != len(edges_df):
        raise ValueError(f"Nonzero count {np.count_nonzero(W_raw)} != edge count {len(edges_df)}")
    if W_raw.max() != CONTRACT["max_raw_weight"]:
        raise ValueError(f"Matrix max weight {W_raw.max()} != {CONTRACT['max_raw_weight']}")

    return CircuitData(
        nodes_df=nodes_df,
        edges_df=edges_df,
        body_ids=body_ids,
        id_to_idx=id_to_idx,
        W_raw=W_raw,
        W_norm=W_norm,
        nt_map=nt_map,
        side_map=side_map,
        type_map=type_map,
        population_map=population_map,
        file_hashes=file_hashes,
    )


def build_signed_weight_matrix(
    circuit: CircuitData,
    sign_map: dict[str, float],
) -> np.ndarray:
    """Build signed weight matrix from normalized weights and neurotransmitter sign map.

    MODEL ASSUMPTION: Signs are assigned based on predicted neurotransmitter, not
    experimentally established synaptic polarity.

    W_signed[post, pre] = sign(nt_of_pre) * W_norm[post, pre]

    Args:
        circuit: Loaded circuit data.
        sign_map: Mapping from neurotransmitter name to sign value.
                  Default convention: {"acetylcholine": +1, "GABA": -1, "glutamate": -1}

    Returns:
        Signed weight matrix W_signed[post, pre].
    """
    W_signed = np.zeros_like(circuit.W_norm)
    for bid in circuit.body_ids:
        nt = circuit.nt_map[bid]
        if nt not in sign_map:
            raise ValueError(
                f"Neurotransmitter '{nt}' for bodyId {bid} not in sign_map. "
                f"Available: {list(sign_map.keys())}"
            )
        col = circuit.id_to_idx[bid]
        sign = sign_map[nt]
        W_signed[:, col] = sign * circuit.W_norm[:, col]
    return W_signed


def verify_named_edges(circuit: CircuitData) -> list[dict[str, Any]]:
    """Verify several named edges against the frozen CSV for W[post,pre] convention.

    Returns list of verification results.
    """
    results = []

    # Pick edges from the CSV file to verify
    # Edge: LC4 81112 -> DNp04 531898, weight=172 (max weight edge)
    test_edges = [
        {"pre": 81112, "post": 531898, "expected_raw": 172, "description": "Max weight edge LC4->DNp04"},
        {"pre": 12349, "post": 531898, "expected_raw": 160, "description": "LC4->DNp04 second heaviest"},
        {"pre": 17054, "post": 11137, "expected_raw": 154, "description": "LC4_R->DNp04_R"},
    ]

    for te in test_edges:
        pre_idx = circuit.id_to_idx.get(te["pre"])
        post_idx = circuit.id_to_idx.get(te["post"])
        if pre_idx is None or post_idx is None:
            results.append({**te, "status": "FAIL", "reason": "bodyId not found"})
            continue

        raw_val = circuit.W_raw[post_idx, pre_idx]  # W[post, pre]
        norm_val = circuit.W_norm[post_idx, pre_idx]
        expected_norm = te["expected_raw"] / CONTRACT["max_raw_weight"]

        ok = (
            raw_val == te["expected_raw"]
            and abs(norm_val - expected_norm) < 1e-10
        )
        results.append({
            **te,
            "actual_raw": float(raw_val),
            "actual_norm": float(norm_val),
            "expected_norm": expected_norm,
            "status": "PASS" if ok else "FAIL",
        })

    return results
