"""
freeze_circuit_v2.py — Phase 3: Freeze and Formalize Circuit v2

Constructs the frozen Circuit v2 from MaleCNS v1.0 source data (feather files).

Circuit v2 expands provisional Circuit v1 to include the complete verified
escape steering and takeoff motor channels identified in Phase 2:
  - LC4   (126 neurons) — looming-sensitive visual projection neurons
  - LPLC2 (185 neurons) — lobula plate / lobula columnar neurons
  - DNp01 (2 neurons)   — primary escape readout (Giant Fiber: unsteered emergency jump)
  - DNp04 (2 neurons)   — directional escape readout (backward takeoff partner)
  - DNp02 (2 neurons)   — directional escape readout (obligate backward takeoff co-factor)
  - DNp11 (2 neurons)   — directional escape readout (forward jump takeoff)
  - DNp06 (2 neurons)   — flight evasive steering readout (threat-induced flight saccades)

Total neurons: 321 (311 visual + 10 descending)

Processing:
  1. Extract all neurons of circuit types from body-annotations feather
  2. Extract neurotransmitter predictions from body-neurotransmitters feather
  3. Extract ALL edges among circuit neurons from connectome-weights feather
  4. Aggregate duplicate (pre, post) pairs by summing weights
  5. Apply w_min=3 threshold (established in Phase 1 config.yaml)
  6. Max-normalize weights (dividing by max weight = 172)
  7. Produce frozen artifacts in connectome/phase3/
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.ipc as ipc


# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION — Phase 2/3 decisions, frozen for Circuit v2
# ═══════════════════════════════════════════════════════════════════

CIRCUIT_TYPES = ["LC4", "LPLC2", "DNp01", "DNp04", "DNp06", "DNp02", "DNp11"]

READOUT_NEURONS = {
    "DNp01": "primary",    # Giant Fiber — unsteered emergency jump trigger
    "DNp04": "secondary",  # Directional takeoff steering (backward jump partner)
    "DNp02": "secondary",  # Directional takeoff steering (obligate backward jump co-factor)
    "DNp11": "secondary",  # Directional takeoff steering (forward jump trigger)
    "DNp06": "secondary",  # Flight evasive steering readout
}

VISUAL_TYPES = {"LC4", "LPLC2"}
DN_TYPES = {"DNp01", "DNp04", "DNp06", "DNp02", "DNp11"}

W_MIN = 3              # Minimum weight threshold
NORMALIZATION = "max"   # Normalization method

CIRCUIT_VERSION = "2.0.0"
CIRCUIT_ID = "circuit_v2"

EXPECTED_COUNTS = {
    "LC4": 126,
    "LPLC2": 185,
    "DNp01": 2,
    "DNp04": 2,
    "DNp06": 2,
    "DNp02": 2,
    "DNp11": 2,
}

# ═══════════════════════════════════════════════════════════════════
# PATHS
# ═══════════════════════════════════════════════════════════════════

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent.parent              # connectome/
DATA_ROOT = BASE_DIR / "data" / "raw"

ANNOTATIONS_PATH = (
    DATA_ROOT / "annotations"
    / "body-annotations-male-cns-v1.0-minconf-0.5.feather"
)
CONNECTIVITY_PATH = (
    DATA_ROOT / "connectivity"
    / "connectome-weights-male-cns-v1.0-minconf-0.5.feather"
)
NT_PATH = (
    DATA_ROOT / "neurotransmitters"
    / "body-neurotransmitters-male-cns-v1.0.feather"
)

OUTPUT_DIR = BASE_DIR / "phase3"


# ═══════════════════════════════════════════════════════════════════
# UTILITIES
# ═══════════════════════════════════════════════════════════════════

def compute_sha256(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def stream_feather_batches(path: Path):
    """Stream an Arrow/Feather IPC file without loading entirely."""
    source = pa.memory_map(str(path), "r")
    try:
        reader = ipc.open_file(source)
        for i in range(reader.num_record_batches):
            yield reader.get_batch(i)
    finally:
        source.close()


def normalize_side(soma_side: str | None, instance: str | None) -> str:
    """Normalize side from MaleCNS annotations."""
    if pd.notna(soma_side):
        s = str(soma_side).strip().upper()
        if s == "L":
            return "left"
        if s == "R":
            return "right"

    if pd.notna(instance):
        inst = str(instance).strip()
        if inst.endswith("_L") or "(L)" in inst:
            return "left"
        if inst.endswith("_R") or "(R)" in inst:
            return "right"

    return "unknown"


def classify_edge(pre_type: str, post_type: str) -> str:
    """Classify an edge based on pre/post neuron types."""
    pre_visual = pre_type in VISUAL_TYPES
    post_visual = post_type in VISUAL_TYPES
    pre_dn = pre_type in DN_TYPES
    post_dn = post_type in DN_TYPES

    if pre_visual and post_dn:
        return "visual_to_readout"
    if pre_visual and post_visual:
        if pre_type == post_type:
            return "intra_population"
        return "cross_visual"
    if pre_dn and post_dn:
        return "inter_readout"
    if pre_dn and post_visual:
        return "readout_to_visual"

    return "other"


# ═══════════════════════════════════════════════════════════════════
# STEP 1: EXTRACT CIRCUIT NEURONS
# ═══════════════════════════════════════════════════════════════════

def extract_neurons() -> pd.DataFrame:
    """Extract all circuit neurons from the annotations feather file."""
    print("Step 1: Extracting circuit neurons from annotations...")

    ann = pd.read_feather(
        ANNOTATIONS_PATH,
        columns=["bodyId", "type", "instance", "somaSide", "superclass"],
    )

    ann["bodyId"] = pd.to_numeric(ann["bodyId"], errors="coerce")
    ann = ann.dropna(subset=["bodyId"]).copy()
    ann["bodyId"] = ann["bodyId"].astype(np.int64)
    ann["type_clean"] = ann["type"].astype(str).str.strip()

    circuit = ann[ann["type_clean"].isin(CIRCUIT_TYPES)].copy()

    if circuit.empty:
        raise RuntimeError("No neurons found for circuit types.")

    circuit["side"] = circuit.apply(
        lambda row: normalize_side(row["somaSide"], row["instance"]),
        axis=1,
    )

    circuit["population"] = circuit["type_clean"].apply(
        lambda t: "visual_input" if t in VISUAL_TYPES else "readout"
    )
    circuit["role"] = circuit["type_clean"].apply(
        lambda t: READOUT_NEURONS.get(t, "looming_sensor")
    )

    circuit = circuit.drop_duplicates(subset=["bodyId"])

    nodes = circuit[
        ["bodyId", "type_clean", "side", "population", "role"]
    ].rename(columns={"type_clean": "type"})

    nodes = nodes.sort_values(
        ["type", "side", "bodyId"]
    ).reset_index(drop=True)

    counts = nodes["type"].value_counts().to_dict()
    for ntype, expected_count in EXPECTED_COUNTS.items():
        actual = counts.get(ntype, 0)
        if actual != expected_count:
            raise RuntimeError(
                f"Population count mismatch for {ntype}: "
                f"expected {expected_count}, got {actual}"
            )

    print(f"  Found {len(nodes)} circuit neurons:")
    for ntype in CIRCUIT_TYPES:
        n = counts[ntype]
        print(f"    {ntype:8s}: {n}")

    return nodes


# ═══════════════════════════════════════════════════════════════════
# STEP 2: EXTRACT NEUROTRANSMITTER PREDICTIONS
# ═══════════════════════════════════════════════════════════════════

def extract_neurotransmitters(body_ids: set[int]) -> pd.DataFrame:
    """Extract neurotransmitter predictions for circuit neurons."""
    print("\nStep 2: Extracting neurotransmitter predictions...")

    nt = pd.read_feather(NT_PATH)
    nt["body"] = pd.to_numeric(nt["body"], errors="coerce")
    nt = nt.dropna(subset=["body"]).copy()
    nt["body"] = nt["body"].astype(np.int64)

    circuit_nt = nt[nt["body"].isin(body_ids)].copy()

    result = circuit_nt[
        [
            "body",
            "predicted_nt",
            "predicted_nt_confidence",
            "consensus_nt",
        ]
    ].rename(columns={"body": "bodyId"})

    result = result.drop_duplicates(subset=["bodyId"])

    missing = body_ids - set(result["bodyId"].tolist())
    if missing:
        print(f"  WARNING: {len(missing)} neurons missing from NT file: {missing}")

    nt_counts = result["predicted_nt"].value_counts()
    print(f"  NT predictions for {len(result)} neurons:")
    for nt_type, count in nt_counts.items():
        print(f"    {nt_type}: {count}")

    return result


# ═══════════════════════════════════════════════════════════════════
# STEP 3: EXTRACT ALL CIRCUIT EDGES
# ═══════════════════════════════════════════════════════════════════

def extract_edges(body_ids: set[int]) -> pd.DataFrame:
    """Extract all edges where BOTH pre and post are circuit neurons."""
    print("\nStep 3: Extracting circuit edges from connectivity...")

    body_array = pa.array(sorted(body_ids), type=pa.int64())

    chunks: list[pd.DataFrame] = []
    batches_scanned = 0

    for batch in stream_feather_batches(CONNECTIVITY_PATH):
        batches_scanned += 1
        table = batch.select(["body_pre", "body_post", "weight"])

        pre = pc.cast(table["body_pre"], pa.int64(), safe=False)
        post = pc.cast(table["body_post"], pa.int64(), safe=False)

        pre_mask = np.asarray(pc.is_in(pre, value_set=body_array))
        post_mask = np.asarray(pc.is_in(post, value_set=body_array))

        mask = pre_mask & post_mask

        if not mask.any():
            continue

        filtered = table.filter(pa.array(mask))
        chunks.append(filtered.to_pandas())

    print(f"  Scanned {batches_scanned} batches")

    if not chunks:
        raise RuntimeError("No edges found among circuit neurons!")

    raw_edges = pd.concat(chunks, ignore_index=True)
    raw_edges["body_pre"] = raw_edges["body_pre"].astype(np.int64)
    raw_edges["body_post"] = raw_edges["body_post"].astype(np.int64)
    raw_edges["weight"] = pd.to_numeric(raw_edges["weight"], errors="raise")

    print(f"  Raw edge rows (before aggregation): {len(raw_edges)}")

    aggregated = (
        raw_edges
        .groupby(["body_pre", "body_post"], as_index=False)["weight"]
        .sum()
    )

    print(f"  Unique directed pairs (after aggregation): {len(aggregated)}")

    filtered = aggregated[aggregated["weight"] >= W_MIN].copy()
    pruned = len(aggregated) - len(filtered)

    print(f"  Edges after w_min={W_MIN} threshold: {len(filtered)}")
    print(f"  Edges pruned: {pruned}")

    return filtered.sort_values("weight", ascending=False).reset_index(drop=True)


# ═══════════════════════════════════════════════════════════════════
# STEP 4: BUILD FROZEN CIRCUIT
# ═══════════════════════════════════════════════════════════════════

def build_frozen_circuit(
    nodes: pd.DataFrame,
    nt_data: pd.DataFrame,
    edges: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Assemble frozen Circuit v2 from extracted components."""
    print("\nStep 4: Building frozen Circuit v2...")

    frozen_nodes = nodes.merge(
        nt_data[["bodyId", "predicted_nt", "predicted_nt_confidence", "consensus_nt"]],
        on="bodyId",
        how="left",
    )

    frozen_nodes["predicted_nt"] = frozen_nodes["predicted_nt"].fillna("UNKNOWN")
    frozen_nodes["consensus_nt"] = frozen_nodes["consensus_nt"].fillna("UNKNOWN")
    frozen_nodes["predicted_nt_confidence"] = (
        frozen_nodes["predicted_nt_confidence"].fillna(0.0)
    )
    frozen_nodes["nt_evidence"] = "predicted"

    type_map = dict(zip(frozen_nodes["bodyId"], frozen_nodes["type"]))
    side_map = dict(zip(frozen_nodes["bodyId"], frozen_nodes["side"]))
    nt_map = dict(zip(frozen_nodes["bodyId"], frozen_nodes["predicted_nt"]))

    frozen_edges = edges.copy()
    frozen_edges.rename(
        columns={"body_pre": "bodyId_pre", "body_post": "bodyId_post"},
        inplace=True,
    )

    frozen_edges["pre_type"] = frozen_edges["bodyId_pre"].map(type_map)
    frozen_edges["pre_side"] = frozen_edges["bodyId_pre"].map(side_map)
    frozen_edges["post_type"] = frozen_edges["bodyId_post"].map(type_map)
    frozen_edges["post_side"] = frozen_edges["bodyId_post"].map(side_map)

    frozen_edges["pre_nt"] = frozen_edges["bodyId_pre"].map(nt_map)

    frozen_edges["edge_class"] = frozen_edges.apply(
        lambda row: classify_edge(row["pre_type"], row["post_type"]),
        axis=1,
    )

    w_max = frozen_edges["weight"].max()
    frozen_edges["weight_normalized"] = frozen_edges["weight"] / w_max

    frozen_edges = frozen_edges[
        [
            "bodyId_pre", "pre_type", "pre_side", "pre_nt",
            "bodyId_post", "post_type", "post_side",
            "weight", "weight_normalized", "edge_class",
        ]
    ]

    frozen_edges = frozen_edges.sort_values(
        "weight", ascending=False
    ).reset_index(drop=True)

    edge_class_counts = frozen_edges["edge_class"].value_counts().to_dict()

    print(f"  Frozen nodes: {len(frozen_nodes)}")
    print(f"  Frozen edges: {len(frozen_edges)}")
    print(f"  Max weight: {w_max}")
    print(f"  Edge classes:")
    for cls, count in sorted(edge_class_counts.items()):
        print(f"    {cls}: {count}")

    readout_summary = {}
    for dn_type, role in READOUT_NEURONS.items():
        dn_nodes = frozen_nodes[frozen_nodes["type"] == dn_type]
        dn_ids = set(dn_nodes["bodyId"].tolist())
        incoming = frozen_edges[frozen_edges["bodyId_post"].isin(dn_ids)]

        per_visual = {}
        for vt in VISUAL_TYPES:
            w = incoming[incoming["pre_type"] == vt]["weight"].sum()
            per_visual[vt] = int(w)

        readout_summary[dn_type] = {
            "role": role,
            "neuron_count": len(dn_ids),
            "body_ids": sorted(dn_ids),
            "sides": dn_nodes["side"].tolist(),
            "total_visual_input": sum(per_visual.values()),
            "input_by_visual_type": per_visual,
        }

    circuit_json = {
        "circuit_id": CIRCUIT_ID,
        "version": CIRCUIT_VERSION,
        "frozen_date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dataset": "MaleCNS v1.0 (male-cns:v1.0)",
        "parameters": {
            "w_min": W_MIN,
            "normalization_method": NORMALIZATION,
            "weight_convention": "W[post, pre] = synapse count from pre to post",
            "weight_type": "unsigned_structural",
        },
        "population_counts": (
            frozen_nodes["type"]
            .value_counts()
            .to_dict()
        ),
        "total_nodes": len(frozen_nodes),
        "total_edges": len(frozen_edges),
        "max_weight": int(w_max),
        "edge_class_counts": edge_class_counts,
        "readout_summary": readout_summary,
        "neurotransmitter_summary": {
            "all_321_neurons_predicted": "acetylcholine",
            "evidence_level": "predicted (MaleCNS v1.0 classifier)",
            "note": (
                "Predicted neurotransmitter is NOT experimentally "
                "established synaptic polarity. All neurons in this "
                "circuit are predicted cholinergic (excitatory), but "
                "this is a classifier output, not a functional assay."
            ),
        },
        "retinotopy": {
            "status": "NOT_AVAILABLE",
            "detail": (
                "MaleCNS v1.0 does not populate retinotopic metadata "
                "(assignedOlHex1, assignedOlHex2) for LC4/LPLC2 neurons. "
                "ROI lobula column identifiers exist as potential proxies "
                "but have not been extracted or validated. No fabricated "
                "visual-angle mapping is included."
            ),
            "proxy_available": "lobula_column_roi_ids",
            "proxy_extracted": False,
        },
        "computational_conventions": {
            "synaptic_weights": (
                "Unsigned structural synapse counts. Phase 4 must decide "
                "how to convert these to model parameters (e.g., gain, "
                "conductance). The frozen weights are the connectome "
                "observation, not a simulation parameter."
            ),
            "excitatory_inhibitory_signs": (
                "All 321 neurons are predicted acetylcholine (excitatory). "
                "Signs are NOT applied to the frozen weights. Phase 4 must "
                "decide sign convention. Predicted NT is stored as metadata."
            ),
            "normalization": (
                f"Max-normalization: weight_normalized = weight / {int(w_max)}. "
                "This is a linear rescaling to [0, 1], preserving relative "
                "connection strengths."
            ),
            "retinotopy_representation": (
                "NOT INCLUDED in Circuit v2. Phase 4 must not fabricate "
                "visual-angle mappings."
            ),
        },
        "nodes": frozen_nodes.to_dict(orient="records"),
        "edges": frozen_edges.to_dict(orient="records"),
    }

    return frozen_nodes, frozen_edges, circuit_json


# ═══════════════════════════════════════════════════════════════════
# STEP 5: COMPUTE DATA PROVENANCE
# ═══════════════════════════════════════════════════════════════════

def compute_provenance() -> dict:
    """Compute checksums and provenance for all source data files."""
    print("\nStep 5: Computing data provenance...")

    provenance = {
        "circuit_id": CIRCUIT_ID,
        "circuit_version": CIRCUIT_VERSION,
        "dataset": {
            "name": "MaleCNS v1.0",
            "identifier": "male-cns:v1.0",
            "server": "https://neuprint.janelia.org",
            "release_note": (
                "June 8, 2026 initial release. MaleCNS has had at least "
                "one post-release annotation revision. The checksums below "
                "pin the exact file versions used."
            ),
        },
        "source_files": {},
        "pipeline": {
            "w_min": W_MIN,
            "normalization": NORMALIZATION,
            "aggregation": "sum duplicate (pre, post) pairs",
            "threshold_application": "after aggregation",
        },
        "software": {
            "python_packages": {},
        },
        "build_timestamp": (
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        ),
    }

    source_files = {
        "body_annotations": ANNOTATIONS_PATH,
        "connectome_weights": CONNECTIVITY_PATH,
        "body_neurotransmitters": NT_PATH,
    }

    for name, path in source_files.items():
        if path.exists():
            sha = compute_sha256(path)
            provenance["source_files"][name] = {
                "filename": path.name,
                "sha256": sha,
                "size_bytes": path.stat().st_size,
            }
            print(f"  {name}: {sha[:16]}...")
        else:
            provenance["source_files"][name] = {
                "filename": path.name,
                "sha256": "FILE_NOT_FOUND",
                "size_bytes": 0,
            }

    try:
        import pandas
        provenance["software"]["python_packages"]["pandas"] = pandas.__version__
    except Exception:
        pass
    try:
        import pyarrow
        provenance["software"]["python_packages"]["pyarrow"] = pyarrow.__version__
    except Exception:
        pass
    try:
        import numpy
        provenance["software"]["python_packages"]["numpy"] = numpy.__version__
    except Exception:
        pass

    return provenance


# ═══════════════════════════════════════════════════════════════════
# STEP 6: BUILD-TIME VALIDATION
# ═══════════════════════════════════════════════════════════════════

def validate_circuit(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
) -> list[str]:
    """Run build-time validation checks for Circuit v2."""
    print("\nStep 6: Running build-time validation...")

    failures: list[str] = []
    checks_passed = 0

    def check(condition: bool, label: str):
        nonlocal checks_passed
        if condition:
            checks_passed += 1
            print(f"  ✓ {label}")
        else:
            failures.append(label)
            print(f"  ✗ FAIL: {label}")

    body_ids = set(nodes["bodyId"].tolist())

    check(len(nodes) == 321, f"Total node count is 321 (got {len(nodes)})")
    check(nodes["bodyId"].is_unique, "No duplicate bodyIds")

    for ntype, expected in EXPECTED_COUNTS.items():
        actual = len(nodes[nodes["type"] == ntype])
        check(actual == expected, f"{ntype} count = {expected} (got {actual})")

    for dn_type in ["DNp01", "DNp04", "DNp06", "DNp02", "DNp11"]:
        dn = nodes[nodes["type"] == dn_type]
        sides = set(dn["side"].tolist())
        check(
            "left" in sides and "right" in sides,
            f"{dn_type} has both L and R neurons",
        )

    check(len(edges) == 11557, f"Circuit has 11,557 edges (got {len(edges)})")

    pre_ids = set(edges["bodyId_pre"].tolist())
    post_ids = set(edges["bodyId_post"].tolist())
    all_edge_ids = pre_ids | post_ids

    check(
        all_edge_ids.issubset(body_ids),
        "All edge endpoints are circuit neurons",
    )

    check(
        (edges["weight"] >= W_MIN).all(),
        f"All edges have weight >= {W_MIN}",
    )

    self_loops = edges[edges["bodyId_pre"] == edges["bodyId_post"]]
    check(
        len(self_loops) == 0,
        f"No self-loop edges (found {len(self_loops)})",
    )

    pairs = list(zip(edges["bodyId_pre"], edges["bodyId_post"]))
    check(
        len(pairs) == len(set(pairs)),
        "No duplicate (pre, post) pairs",
    )

    w_max = edges["weight"].max()
    check(w_max == 172, f"Max weight is 172 (got {w_max})")
    check(
        (edges["weight_normalized"] >= 0.0).all(),
        "All normalized weights are non-negative",
    )
    check(
        (edges["weight_normalized"] <= 1.0).all(),
        "All normalized weights are <= 1.0",
    )

    check(
        (nodes["predicted_nt"] == "acetylcholine").all(),
        "All nodes have predicted_nt = acetylcholine",
    )

    print(f"\n  Build validation: {checks_passed} checks passed, {len(failures)} failed")
    return failures


# ═══════════════════════════════════════════════════════════════════
# STEP 7: SAVE ARTIFACTS
# ═══════════════════════════════════════════════════════════════════

def save_artifacts(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    circuit_json: dict,
    provenance: dict,
    validation_failures: list[str],
):
    """Save all Circuit v2 frozen artifacts to connectome/phase3/."""
    print("\nStep 7: Saving frozen Circuit v2 artifacts...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    nodes_path = OUTPUT_DIR / "circuit_v2_nodes.csv"
    nodes.to_csv(nodes_path, index=False)
    print(f"  Saved: {nodes_path} ({len(nodes)} rows)")

    edges_path = OUTPUT_DIR / "circuit_v2_edges.csv"
    edges.to_csv(edges_path, index=False)
    print(f"  Saved: {edges_path} ({len(edges)} rows)")

    json_path = OUTPUT_DIR / "circuit_v2.json"
    with open(json_path, "w") as f:
        json.dump(circuit_json, f, indent=2)
    print(f"  Saved: {json_path} ({json_path.stat().st_size / 1024 / 1024:.1f} MB)")

    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Circuit v2 Schema — Drosophila Visual Escape Circuit",
        "description": "Schema definition for Circuit v2 nodes, edges, and metadata.",
        "circuit_id": "circuit_v2",
        "version": "2.0.0",
        "nodes": {
            "format": "CSV and JSON",
            "columns": {
                "bodyId": "int64 — unique identifier in MaleCNS v1.0",
                "type": "string — neuron type annotation",
                "side": "string — soma hemisphere (left, right)",
                "population": "string — visual_input or readout",
                "role": "string — sensory/readout function",
                "predicted_nt": "string — classifier-predicted neurotransmitter",
                "predicted_nt_confidence": "float — classifier probability",
                "consensus_nt": "string — consensus neurotransmitter",
                "nt_evidence": "string — evidence status (predicted)",
            },
        },
        "edges": {
            "format": "CSV and JSON",
            "columns": {
                "bodyId_pre": "int64 — presynaptic neuron ID",
                "pre_type": "string — presynaptic neuron type",
                "pre_side": "string — presynaptic hemisphere",
                "pre_nt": "string — presynaptic neurotransmitter",
                "bodyId_post": "int64 — postsynaptic neuron ID",
                "post_type": "string — postsynaptic neuron type",
                "post_side": "string — postsynaptic hemisphere",
                "weight": "int64 — synapse count (w >= 3)",
                "weight_normalized": "float — weight / max_weight (max=172)",
                "edge_class": "string — visual_to_readout, intra_population, cross_visual, inter_readout, readout_to_visual",
            },
        },
    }

    schema_path = OUTPUT_DIR / "circuit_v2_schema.json"
    with open(schema_path, "w") as f:
        json.dump(schema, f, indent=2)
    print(f"  Saved: {schema_path}")

    prov_path = OUTPUT_DIR / "circuit_v2_provenance.json"
    with open(prov_path, "w") as f:
        json.dump(provenance, f, indent=2)
    print(f"  Saved: {prov_path}")

    val_path = OUTPUT_DIR / "circuit_v2_build_validation.json"
    with open(val_path, "w") as f:
        json.dump(
            {
                "status": "PASS" if not validation_failures else "FAIL",
                "circuit_id": CIRCUIT_ID,
                "version": CIRCUIT_VERSION,
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "failures": validation_failures,
            },
            f,
            indent=2,
        )
    print(f"  Saved: {val_path}")


def main():
    print("=" * 60)
    print("FREEZING CIRCUIT v2 — DROSOPHILA VISUAL ESCAPE")
    print("=" * 60)

    nodes = extract_neurons()
    body_ids = set(nodes["bodyId"].tolist())

    nt_data = extract_neurotransmitters(body_ids)
    edges = extract_edges(body_ids)

    frozen_nodes, frozen_edges, circuit_json = build_frozen_circuit(
        nodes, nt_data, edges
    )

    provenance = compute_provenance()
    failures = validate_circuit(frozen_nodes, frozen_edges)

    if failures:
        print(f"\nFATAL: Build validation failed with {len(failures)} errors!")
        sys.exit(1)

    save_artifacts(
        frozen_nodes, frozen_edges, circuit_json, provenance, failures
    )

    print("\n" + "=" * 60)
    print("CIRCUIT v2 FREEZE COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
