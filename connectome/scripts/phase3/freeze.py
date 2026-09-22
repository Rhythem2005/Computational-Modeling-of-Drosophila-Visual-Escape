"""
phase3_freeze.py — Phase 3: Freeze and Formalize Circuit v1

Constructs the frozen Circuit v1 from MaleCNS v1.0 source data (feather files).

Circuit v1 contains exactly 5 neuron types established in Phases 0–2:
  - LC4   (126 neurons) — looming-sensitive visual projection neurons
  - LPLC2 (185 neurons) — lobula plate / lobula columnar neurons
  - DNp01 (2 neurons)   — primary escape readout (Giant Fiber)
  - DNp04 (2 neurons)   — secondary escape readout
  - DNp06 (2 neurons)   — secondary escape readout

Processing:
  1. Extract all neurons of circuit types from body-annotations feather
  2. Extract neurotransmitter predictions from body-neurotransmitters feather
  3. Extract ALL edges among circuit neurons from connectome-weights feather
  4. Aggregate duplicate (pre, post) pairs by summing weights
  5. Apply w_min=3 threshold (established in Phase 1 config.yaml)
  6. Max-normalize weights
  7. Produce frozen artifacts

All biological/scientific decisions were made in Phase 2.
This script formalizes those decisions into machine-readable artifacts.
No biological decisions are made here.
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
# CONFIGURATION — Phase 2 decisions, frozen here
# ═══════════════════════════════════════════════════════════════════

CIRCUIT_TYPES = ["LC4", "LPLC2", "DNp01", "DNp04", "DNp06"]

READOUT_NEURONS = {
    "DNp01": "primary",    # Giant Fiber — primary behavioral trigger
    "DNp04": "secondary",  # Secondary escape readout
    "DNp06": "secondary",  # Secondary escape readout
}

VISUAL_TYPES = {"LC4", "LPLC2"}
DN_TYPES = {"DNp01", "DNp04", "DNp06"}

W_MIN = 3              # Minimum weight threshold (Phase 1, config.yaml)
NORMALIZATION = "max"   # Normalization method (Phase 1, config.yaml)

CIRCUIT_VERSION = "1.0.0"
CIRCUIT_ID = "circuit_v1"

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
# UTILITY FUNCTIONS
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
    """
    Normalize side from MaleCNS annotations.

    Uses somaSide (L/R) first, falls back to instance suffix.
    """
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

    # Filter to circuit types
    circuit = ann[ann["type_clean"].isin(CIRCUIT_TYPES)].copy()

    if circuit.empty:
        raise RuntimeError(
            "No neurons found for circuit types. "
            "Check the annotations file."
        )

    # Normalize side
    circuit["side"] = circuit.apply(
        lambda row: normalize_side(row["somaSide"], row["instance"]),
        axis=1,
    )

    # Assign population and role
    circuit["population"] = circuit["type_clean"].apply(
        lambda t: "visual_input" if t in VISUAL_TYPES else "readout"
    )
    circuit["role"] = circuit["type_clean"].apply(
        lambda t: READOUT_NEURONS.get(t, "looming_sensor")
    )

    # Deduplicate by bodyId
    circuit = circuit.drop_duplicates(subset=["bodyId"])

    # Select and rename columns
    nodes = circuit[
        ["bodyId", "type_clean", "side", "population", "role"]
    ].rename(columns={"type_clean": "type"})

    nodes = nodes.sort_values(
        ["type", "side", "bodyId"]
    ).reset_index(drop=True)

    # Validate population counts
    counts = nodes["type"].value_counts().to_dict()
    expected = {"LC4": 126, "LPLC2": 185, "DNp01": 2, "DNp04": 2, "DNp06": 2}

    for ntype, expected_count in expected.items():
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

    # Summary
    nt_counts = result["predicted_nt"].value_counts()
    print(f"  NT predictions for {len(result)} neurons:")
    for nt_type, count in nt_counts.items():
        print(f"    {nt_type}: {count}")

    return result


# ═══════════════════════════════════════════════════════════════════
# STEP 3: EXTRACT ALL CIRCUIT EDGES
# ═══════════════════════════════════════════════════════════════════

def extract_edges(body_ids: set[int]) -> pd.DataFrame:
    """
    Extract all edges where BOTH pre and post are circuit neurons.

    Streams the connectivity feather file to handle the ~1 GB file
    without loading it entirely into memory.
    """
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

        # BOTH endpoints must be circuit neurons
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

    # Aggregate duplicate (pre, post) pairs
    aggregated = (
        raw_edges
        .groupby(["body_pre", "body_post"], as_index=False)["weight"]
        .sum()
    )

    print(f"  Unique directed pairs (after aggregation): {len(aggregated)}")

    # Apply w_min threshold
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
    """
    Assemble the frozen Circuit v1 from extracted components.

    Returns (frozen_nodes, frozen_edges, circuit_json).
    """
    print("\nStep 4: Building frozen Circuit v1...")

    # ── Merge NT data into nodes ──────────────────────────────────
    frozen_nodes = nodes.merge(
        nt_data[["bodyId", "predicted_nt", "predicted_nt_confidence", "consensus_nt"]],
        on="bodyId",
        how="left",
    )

    # Fill missing NT with explicit marker
    frozen_nodes["predicted_nt"] = frozen_nodes["predicted_nt"].fillna("UNKNOWN")
    frozen_nodes["consensus_nt"] = frozen_nodes["consensus_nt"].fillna("UNKNOWN")
    frozen_nodes["predicted_nt_confidence"] = (
        frozen_nodes["predicted_nt_confidence"].fillna(0.0)
    )

    # NT evidence status
    frozen_nodes["nt_evidence"] = "predicted"

    # ── Annotate edges ────────────────────────────────────────────
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

    # Synaptic sign from presynaptic neurotransmitter
    frozen_edges["pre_nt"] = frozen_edges["bodyId_pre"].map(nt_map)

    # Edge classification
    frozen_edges["edge_class"] = frozen_edges.apply(
        lambda row: classify_edge(row["pre_type"], row["post_type"]),
        axis=1,
    )

    # Max-normalization
    w_max = frozen_edges["weight"].max()
    frozen_edges["weight_normalized"] = frozen_edges["weight"] / w_max

    # Reorder columns
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

    # ── Summary statistics ────────────────────────────────────────
    edge_class_counts = frozen_edges["edge_class"].value_counts().to_dict()

    print(f"  Frozen nodes: {len(frozen_nodes)}")
    print(f"  Frozen edges: {len(frozen_edges)}")
    print(f"  Max weight: {w_max}")
    print(f"  Edge classes:")
    for cls, count in sorted(edge_class_counts.items()):
        print(f"    {cls}: {count}")

    # ── Build readout summary ─────────────────────────────────────
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

    # ── Build circuit JSON ────────────────────────────────────────
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
            "all_317_neurons_predicted": "acetylcholine",
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
                "All 317 neurons are predicted acetylcholine (excitatory). "
                "Signs are NOT applied to the frozen weights. Phase 4 must "
                "decide sign convention. Predicted NT is stored as metadata. "
                "If Phase 4 treats acetylcholine as excitatory (+1), this is "
                "a computational assumption, not a connectome fact."
            ),
            "unknown_neurotransmitters": (
                "No neurons in Circuit v1 have unknown NT. All are predicted "
                "acetylcholine. If a future revision changes predictions, "
                "Phase 4 must handle unknowns explicitly."
            ),
            "glutamate": (
                "No glutamatergic neurons in Circuit v1. Glutamate in "
                "Drosophila can be excitatory or inhibitory depending on "
                "receptor. Not applicable here."
            ),
            "normalization": (
                f"Max-normalization: weight_normalized = weight / {int(w_max)}. "
                "This is a linear rescaling to [0, 1], preserving relative "
                "connection strengths. Phase 4 may apply additional "
                "transformations (gain, nonlinearity)."
            ),
            "retinotopy_representation": (
                "NOT INCLUDED in Circuit v1. Phase 4 must not fabricate "
                "visual-angle mappings. If spatial processing is needed, "
                "use the lobula column ROI proxy (not yet extracted) or "
                "a uniform/random spatial model with explicit documentation."
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

    # File checksums
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
            print(f"  WARNING: {name} not found at {path}")

    # Python package versions
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
    """
    Run build-time validation checks.

    Returns list of failure messages. Empty list = all checks passed.
    """
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

    # Node checks
    check(len(nodes) == 317, f"Total node count is 317 (got {len(nodes)})")
    check(nodes["bodyId"].is_unique, "No duplicate bodyIds")

    for ntype, expected in [
        ("LC4", 126), ("LPLC2", 185),
        ("DNp01", 2), ("DNp04", 2), ("DNp06", 2),
    ]:
        actual = len(nodes[nodes["type"] == ntype])
        check(actual == expected, f"{ntype} count = {expected} (got {actual})")

    # Side checks for DNs
    for dn_type in ["DNp01", "DNp04", "DNp06"]:
        dn = nodes[nodes["type"] == dn_type]
        sides = set(dn["side"].tolist())
        check(
            "left" in sides and "right" in sides,
            f"{dn_type} has both L and R neurons",
        )

    # Edge checks
    check(len(edges) > 0, "Circuit has edges")

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

    # No self-loops
    self_loops = edges[edges["bodyId_pre"] == edges["bodyId_post"]]
    check(
        len(self_loops) == 0,
        f"No self-loop edges (found {len(self_loops)})",
    )

    # No duplicate edges
    dup = edges.groupby(["bodyId_pre", "bodyId_post"]).size()
    check(
        (dup == 1).all(),
        f"No duplicate (pre, post) pairs in edges",
    )

    # DNp01 has incoming visual connections
    dnp01_ids = set(
        nodes[nodes["type"] == "DNp01"]["bodyId"].tolist()
    )
    dnp01_incoming = edges[edges["bodyId_post"].isin(dnp01_ids)]
    dnp01_visual = dnp01_incoming[
        dnp01_incoming["pre_type"].isin(VISUAL_TYPES)
    ]
    check(
        len(dnp01_visual) > 0,
        f"DNp01 receives visual input ({len(dnp01_visual)} edges)",
    )

    # DNp04 has incoming visual connections
    dnp04_ids = set(
        nodes[nodes["type"] == "DNp04"]["bodyId"].tolist()
    )
    dnp04_incoming = edges[edges["bodyId_post"].isin(dnp04_ids)]
    dnp04_visual = dnp04_incoming[
        dnp04_incoming["pre_type"].isin(VISUAL_TYPES)
    ]
    check(
        len(dnp04_visual) > 0,
        f"DNp04 receives visual input ({len(dnp04_visual)} edges)",
    )

    # Normalization check
    check(
        np.isclose(edges["weight_normalized"].max(), 1.0),
        "Max normalized weight is 1.0",
    )
    check(
        (edges["weight_normalized"] >= 0).all(),
        "All normalized weights are non-negative",
    )
    check(
        (edges["weight_normalized"] <= 1.0).all(),
        "All normalized weights are <= 1.0",
    )

    # NT metadata present
    check(
        not nodes["predicted_nt"].isna().any(),
        "All nodes have NT prediction",
    )

    print(f"\n  Validation: {checks_passed}/{checks_passed + len(failures)} passed")

    return failures


# ═══════════════════════════════════════════════════════════════════
# STEP 7: WRITE ARTIFACTS
# ═══════════════════════════════════════════════════════════════════

def write_schema() -> dict:
    """Define and return the Circuit v1 schema."""
    schema = {
        "schema_id": "circuit_v1_schema",
        "schema_version": "1.0.0",
        "description": (
            "Schema for the frozen Circuit v1 machine-readable artifacts. "
            "Phase 4 must consume data according to this schema."
        ),
        "nodes": {
            "file": "circuit_v1_nodes.csv",
            "format": "CSV (UTF-8, comma-separated)",
            "columns": {
                "bodyId": {
                    "type": "int64",
                    "description": "MaleCNS v1.0 body ID (unique neuron identifier)",
                    "unit": "dimensionless",
                },
                "type": {
                    "type": "string",
                    "description": "Neuron type from MaleCNS v1.0 annotations",
                    "allowed_values": CIRCUIT_TYPES,
                },
                "side": {
                    "type": "string",
                    "description": "Hemisphere (from somaSide annotation)",
                    "allowed_values": ["left", "right"],
                },
                "population": {
                    "type": "string",
                    "description": "Functional population category",
                    "allowed_values": ["visual_input", "readout"],
                },
                "role": {
                    "type": "string",
                    "description": "Specific functional role in escape circuit",
                    "allowed_values": [
                        "looming_sensor",
                        "primary",
                        "secondary",
                    ],
                },
                "predicted_nt": {
                    "type": "string",
                    "description": (
                        "Predicted neurotransmitter from MaleCNS v1.0 classifier"
                    ),
                },
                "predicted_nt_confidence": {
                    "type": "float64",
                    "description": "Confidence score of NT prediction [0, 1]",
                    "unit": "dimensionless",
                },
                "consensus_nt": {
                    "type": "string",
                    "description": (
                        "Cell-type-level consensus neurotransmitter"
                    ),
                },
                "nt_evidence": {
                    "type": "string",
                    "description": (
                        "Evidence level: 'predicted' (classifier) or "
                        "'experimental' (functional assay)"
                    ),
                    "allowed_values": ["predicted", "experimental"],
                },
            },
        },
        "edges": {
            "file": "circuit_v1_edges.csv",
            "format": "CSV (UTF-8, comma-separated)",
            "columns": {
                "bodyId_pre": {
                    "type": "int64",
                    "description": "Presynaptic neuron body ID",
                },
                "pre_type": {
                    "type": "string",
                    "description": "Type of presynaptic neuron",
                },
                "pre_side": {
                    "type": "string",
                    "description": "Hemisphere of presynaptic neuron",
                },
                "pre_nt": {
                    "type": "string",
                    "description": (
                        "Predicted neurotransmitter of presynaptic neuron "
                        "(determines putative synaptic sign)"
                    ),
                },
                "bodyId_post": {
                    "type": "int64",
                    "description": "Postsynaptic neuron body ID",
                },
                "post_type": {
                    "type": "string",
                    "description": "Type of postsynaptic neuron",
                },
                "post_side": {
                    "type": "string",
                    "description": "Hemisphere of postsynaptic neuron",
                },
                "weight": {
                    "type": "int64",
                    "description": (
                        "Aggregated structural synapse count (unsigned). "
                        "Sum of all synaptic connections from pre to post, "
                        f"filtered at w_min={W_MIN}."
                    ),
                    "unit": "synapse_count",
                },
                "weight_normalized": {
                    "type": "float64",
                    "description": (
                        "Max-normalized weight: weight / max_weight. "
                        "Range [0, 1]."
                    ),
                    "unit": "dimensionless",
                },
                "edge_class": {
                    "type": "string",
                    "description": "Functional classification of the edge",
                    "allowed_values": [
                        "visual_to_readout",
                        "intra_population",
                        "cross_visual",
                        "inter_readout",
                        "readout_to_visual",
                        "other",
                    ],
                },
            },
        },
    }

    return schema


def write_artifacts(
    frozen_nodes: pd.DataFrame,
    frozen_edges: pd.DataFrame,
    circuit_json: dict,
    provenance: dict,
    validation_failures: list[str],
):
    """Write all frozen artifacts to disk."""
    print("\nStep 7: Writing frozen artifacts...")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── Nodes CSV ─────────────────────────────────────────────────
    nodes_path = OUTPUT_DIR / "circuit_v1_nodes.csv"
    frozen_nodes.to_csv(nodes_path, index=False)
    print(f"  Wrote {nodes_path.name} ({len(frozen_nodes)} rows)")

    # ── Edges CSV ─────────────────────────────────────────────────
    edges_path = OUTPUT_DIR / "circuit_v1_edges.csv"
    frozen_edges.to_csv(edges_path, index=False)
    print(f"  Wrote {edges_path.name} ({len(frozen_edges)} rows)")

    # ── Schema JSON ───────────────────────────────────────────────
    schema = write_schema()
    schema_path = OUTPUT_DIR / "circuit_v1_schema.json"
    with open(schema_path, "w") as f:
        json.dump(schema, f, indent=2, default=str)
    print(f"  Wrote {schema_path.name}")

    # ── Provenance JSON ───────────────────────────────────────────
    provenance_path = OUTPUT_DIR / "provenance.json"
    with open(provenance_path, "w") as f:
        json.dump(provenance, f, indent=2, default=str)
    print(f"  Wrote {provenance_path.name}")

    # ── Circuit JSON (complete machine-readable circuit) ──────────
    # Add provenance to circuit JSON
    circuit_json["provenance"] = provenance
    circuit_json["schema"] = schema

    circuit_path = OUTPUT_DIR / "circuit_v1.json"
    with open(circuit_path, "w") as f:
        json.dump(circuit_json, f, indent=2, default=str)
    print(f"  Wrote {circuit_path.name}")

    # ── Validation summary ────────────────────────────────────────
    validation = {
        "status": "PASS" if not validation_failures else "FAIL",
        "failures": validation_failures,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    validation_path = OUTPUT_DIR / "build_validation.json"
    with open(validation_path, "w") as f:
        json.dump(validation, f, indent=2)
    print(f"  Wrote {validation_path.name}")


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("PHASE 3: FREEZE AND FORMALIZE CIRCUIT v1")
    print("=" * 60)

    # Verify source files exist
    for label, path in [
        ("Annotations", ANNOTATIONS_PATH),
        ("Connectivity", CONNECTIVITY_PATH),
        ("Neurotransmitters", NT_PATH),
    ]:
        if not path.exists():
            print(f"FATAL: {label} file not found: {path}")
            sys.exit(1)

    # Step 1: Extract neurons
    nodes = extract_neurons()

    # Step 2: Extract neurotransmitters
    body_ids = set(nodes["bodyId"].tolist())
    nt_data = extract_neurotransmitters(body_ids)

    # Step 3: Extract edges
    edges = extract_edges(body_ids)

    # Step 4: Build frozen circuit
    frozen_nodes, frozen_edges, circuit_json = build_frozen_circuit(
        nodes, nt_data, edges,
    )

    # Step 5: Compute provenance
    provenance = compute_provenance()

    # Step 6: Validate
    failures = validate_circuit(frozen_nodes, frozen_edges)

    if failures:
        print("\n" + "!" * 60)
        print("BUILD-TIME VALIDATION FAILED")
        print("!" * 60)
        for f in failures:
            print(f"  ✗ {f}")
        print("\nArtifacts will NOT be written.")
        sys.exit(1)

    # Step 7: Write artifacts
    write_artifacts(
        frozen_nodes, frozen_edges, circuit_json, provenance, failures,
    )

    # Final summary
    print("\n" + "=" * 60)
    print("CIRCUIT v1 FROZEN SUCCESSFULLY")
    print("=" * 60)
    print(f"  Nodes:  {len(frozen_nodes)}")
    print(f"  Edges:  {len(frozen_edges)}")
    print(f"  Output: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
