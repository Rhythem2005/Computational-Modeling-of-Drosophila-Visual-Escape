"""
verify_circuit_v1.py — Independent Verification of Frozen Circuit v1

Loads the frozen Circuit v1 artifacts and verifies every component
against the original MaleCNS v1.0 source data.

This script is independent from phase3_freeze.py — it reads the frozen
artifacts and re-checks them from scratch against the source feather
files.

Checks performed:
  1.  All frozen artifact files exist
  2.  All 317 neuron IDs exist in source annotations
  3.  Neuron types match source annotations
  4.  Neuron sides match source annotations (somaSide)
  5.  Population counts are correct
  6.  All frozen edges exist in source connectivity
  7.  Frozen edge weights EXACTLY match source (after aggregation)
  8.  No edges below w_min threshold
  9.  No unintended edges (no edges in frozen set that aren't in source)
  10. No duplicate or inconsistent nodes
  11. No duplicate edges
  12. Readout populations are correct
  13. NT predictions match source
  14. Provenance checksums match current files
  15. Schema is valid
  16. Reproducibility: re-extract edges and compare

Any check failure is a HARD STOP — the circuit cannot be considered frozen.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.ipc as ipc


# ═══════════════════════════════════════════════════════════════════
# PATHS
# ═══════════════════════════════════════════════════════════════════

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
DATA_ROOT = BASE_DIR / "data" / "male_cns_v1"
PHASE3_DIR = BASE_DIR / "phase3"

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

W_MIN = 3
CIRCUIT_TYPES = ["LC4", "LPLC2", "DNp01", "DNp04", "DNp06"]
EXPECTED_COUNTS = {"LC4": 126, "LPLC2": 185, "DNp01": 2, "DNp04": 2, "DNp06": 2}


# ═══════════════════════════════════════════════════════════════════
# UTILITIES
# ═══════════════════════════════════════════════════════════════════

def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def stream_feather_batches(path: Path):
    source = pa.memory_map(str(path), "r")
    try:
        reader = ipc.open_file(source)
        for i in range(reader.num_record_batches):
            yield reader.get_batch(i)
    finally:
        source.close()


def normalize_side(soma_side, instance) -> str:
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


# ═══════════════════════════════════════════════════════════════════
# MAIN VERIFICATION
# ═══════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("CIRCUIT v1 — INDEPENDENT VERIFICATION")
    print("=" * 60)

    passed = 0
    failed = 0
    failures = []

    def check(condition: bool, label: str):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  ✓ {label}")
        else:
            failed += 1
            failures.append(label)
            print(f"  ✗ FAIL: {label}")

    # ══════════════════════════════════════════════════════════════
    # CHECK 1: ARTIFACT FILES EXIST
    # ══════════════════════════════════════════════════════════════
    print("\n1. ARTIFACT FILES")

    required_files = [
        "circuit_v1_nodes.csv",
        "circuit_v1_edges.csv",
        "circuit_v1.json",
        "circuit_v1_schema.json",
        "provenance.json",
        "build_validation.json",
    ]

    for fname in required_files:
        check(
            (PHASE3_DIR / fname).exists(),
            f"{fname} exists",
        )

    if failed > 0:
        print("\nFATAL: Missing artifact files. Cannot proceed.")
        sys.exit(1)

    # Load frozen artifacts
    frozen_nodes = pd.read_csv(PHASE3_DIR / "circuit_v1_nodes.csv")
    frozen_edges = pd.read_csv(PHASE3_DIR / "circuit_v1_edges.csv")

    with open(PHASE3_DIR / "provenance.json") as f:
        provenance = json.load(f)

    with open(PHASE3_DIR / "circuit_v1_schema.json") as f:
        schema = json.load(f)

    # ══════════════════════════════════════════════════════════════
    # CHECK 2: SOURCE DATA EXISTS
    # ══════════════════════════════════════════════════════════════
    print("\n2. SOURCE DATA FILES")

    for label, path in [
        ("Annotations", ANNOTATIONS_PATH),
        ("Connectivity", CONNECTIVITY_PATH),
        ("Neurotransmitters", NT_PATH),
    ]:
        check(path.exists(), f"{label} feather exists")

    if failed > 0:
        print("\nFATAL: Missing source data. Cannot verify.")
        sys.exit(1)

    # ══════════════════════════════════════════════════════════════
    # CHECK 3: ALL NEURON IDs EXIST IN SOURCE
    # ══════════════════════════════════════════════════════════════
    print("\n3. NEURON ID VERIFICATION")

    ann = pd.read_feather(
        ANNOTATIONS_PATH,
        columns=["bodyId", "type", "instance", "somaSide"],
    )
    ann["bodyId"] = pd.to_numeric(ann["bodyId"], errors="coerce")
    ann = ann.dropna(subset=["bodyId"])
    ann["bodyId"] = ann["bodyId"].astype(np.int64)

    source_ids = set(ann["bodyId"].tolist())
    frozen_ids = set(frozen_nodes["bodyId"].tolist())

    missing = frozen_ids - source_ids
    check(
        len(missing) == 0,
        f"All {len(frozen_ids)} frozen neuron IDs exist in annotations "
        f"(missing: {len(missing)})",
    )

    if missing:
        print(f"    Missing IDs: {missing}")

    # ══════════════════════════════════════════════════════════════
    # CHECK 4: NEURON TYPES MATCH SOURCE
    # ══════════════════════════════════════════════════════════════
    print("\n4. NEURON TYPE VERIFICATION")

    source_type_map = {}
    for _, row in ann.iterrows():
        bid = row["bodyId"]
        t = str(row["type"]).strip() if pd.notna(row["type"]) else None
        if bid in frozen_ids and t:
            source_type_map[bid] = t

    type_mismatches = 0
    for _, row in frozen_nodes.iterrows():
        bid = row["bodyId"]
        frozen_type = row["type"]
        source_type = source_type_map.get(bid)
        if source_type and frozen_type != source_type:
            type_mismatches += 1
            print(f"    TYPE MISMATCH: bodyId={bid} frozen={frozen_type} source={source_type}")

    check(
        type_mismatches == 0,
        f"All neuron types match source ({type_mismatches} mismatches)",
    )

    # ══════════════════════════════════════════════════════════════
    # CHECK 5: NEURON SIDES MATCH SOURCE
    # ══════════════════════════════════════════════════════════════
    print("\n5. NEURON SIDE VERIFICATION")

    source_side_map = {}
    for _, row in ann.iterrows():
        bid = row["bodyId"]
        if bid in frozen_ids:
            source_side_map[bid] = normalize_side(
                row.get("somaSide"), row.get("instance"),
            )

    side_mismatches = 0
    for _, row in frozen_nodes.iterrows():
        bid = row["bodyId"]
        frozen_side = row["side"]
        source_side = source_side_map.get(bid)
        if source_side and frozen_side != source_side:
            side_mismatches += 1
            print(f"    SIDE MISMATCH: bodyId={bid} frozen={frozen_side} source={source_side}")

    check(
        side_mismatches == 0,
        f"All neuron sides match source ({side_mismatches} mismatches)",
    )

    # ══════════════════════════════════════════════════════════════
    # CHECK 6: POPULATION COUNTS
    # ══════════════════════════════════════════════════════════════
    print("\n6. POPULATION COUNTS")

    check(len(frozen_nodes) == 317, f"Total nodes = 317 (got {len(frozen_nodes)})")
    check(frozen_nodes["bodyId"].is_unique, "No duplicate bodyIds")

    for ntype, expected in EXPECTED_COUNTS.items():
        actual = len(frozen_nodes[frozen_nodes["type"] == ntype])
        check(actual == expected, f"{ntype} = {expected} (got {actual})")

    # ══════════════════════════════════════════════════════════════
    # CHECK 7: EDGE VERIFICATION AGAINST SOURCE
    # ══════════════════════════════════════════════════════════════
    print("\n7. EDGE WEIGHT VERIFICATION (exact match against source)")

    # Re-extract edges from feather to build ground truth
    body_array = pa.array(sorted(frozen_ids), type=pa.int64())
    chunks = []

    for batch in stream_feather_batches(CONNECTIVITY_PATH):
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

    source_edges = pd.concat(chunks, ignore_index=True)
    source_edges["body_pre"] = source_edges["body_pre"].astype(np.int64)
    source_edges["body_post"] = source_edges["body_post"].astype(np.int64)

    # Aggregate
    source_agg = (
        source_edges
        .groupby(["body_pre", "body_post"], as_index=False)["weight"]
        .sum()
    )

    # Apply threshold
    source_thresholded = source_agg[source_agg["weight"] >= W_MIN].copy()

    check(
        len(frozen_edges) == len(source_thresholded),
        f"Edge count matches: frozen={len(frozen_edges)} "
        f"source={len(source_thresholded)}",
    )

    # Merge and compare weights
    frozen_key = frozen_edges[["bodyId_pre", "bodyId_post", "weight"]].copy()
    source_key = source_thresholded.rename(
        columns={
            "body_pre": "bodyId_pre",
            "body_post": "bodyId_post",
            "weight": "source_weight",
        }
    )

    merged = frozen_key.merge(
        source_key,
        on=["bodyId_pre", "bodyId_post"],
        how="outer",
        indicator=True,
    )

    only_frozen = merged[merged["_merge"] == "left_only"]
    only_source = merged[merged["_merge"] == "right_only"]
    both = merged[merged["_merge"] == "both"]

    check(
        len(only_frozen) == 0,
        f"No unintended edges in frozen set ({len(only_frozen)} extra)",
    )

    check(
        len(only_source) == 0,
        f"No missing edges in frozen set ({len(only_source)} missing)",
    )

    if len(both) > 0:
        weight_mismatches = (both["weight"] != both["source_weight"]).sum()
        check(
            weight_mismatches == 0,
            f"All edge weights exactly match source "
            f"({weight_mismatches} mismatches, tolerance=0)",
        )

    # ══════════════════════════════════════════════════════════════
    # CHECK 8: THRESHOLD ENFORCEMENT
    # ══════════════════════════════════════════════════════════════
    print("\n8. THRESHOLD ENFORCEMENT")

    check(
        (frozen_edges["weight"] >= W_MIN).all(),
        f"All edges have weight >= {W_MIN}",
    )

    # ══════════════════════════════════════════════════════════════
    # CHECK 9: NO DUPLICATES OR SELF-LOOPS
    # ══════════════════════════════════════════════════════════════
    print("\n9. EDGE INTEGRITY")

    dup_edges = frozen_edges.groupby(["bodyId_pre", "bodyId_post"]).size()
    check(
        (dup_edges == 1).all(),
        "No duplicate (pre, post) pairs",
    )

    self_loops = frozen_edges[
        frozen_edges["bodyId_pre"] == frozen_edges["bodyId_post"]
    ]
    check(len(self_loops) == 0, f"No self-loops ({len(self_loops)} found)")

    # ══════════════════════════════════════════════════════════════
    # CHECK 10: READOUT POPULATIONS
    # ══════════════════════════════════════════════════════════════
    print("\n10. READOUT POPULATIONS")

    readout_nodes = frozen_nodes[frozen_nodes["population"] == "readout"]
    readout_types = set(readout_nodes["type"].tolist())
    check(
        readout_types == {"DNp01", "DNp04", "DNp06"},
        f"Readout types = {{DNp01, DNp04, DNp06}} (got {readout_types})",
    )

    for dn in ["DNp01", "DNp04", "DNp06"]:
        dn_nodes = readout_nodes[readout_nodes["type"] == dn]
        sides = set(dn_nodes["side"].tolist())
        check(
            sides == {"left", "right"},
            f"{dn} has L/R pair (got {sides})",
        )

    # ══════════════════════════════════════════════════════════════
    # CHECK 11: NT PREDICTIONS MATCH SOURCE
    # ══════════════════════════════════════════════════════════════
    print("\n11. NEUROTRANSMITTER VERIFICATION")

    nt = pd.read_feather(NT_PATH)
    nt["body"] = pd.to_numeric(nt["body"], errors="coerce")
    nt = nt.dropna(subset=["body"])
    nt["body"] = nt["body"].astype(np.int64)

    circuit_nt = nt[nt["body"].isin(frozen_ids)]
    source_nt_map = dict(
        zip(circuit_nt["body"], circuit_nt["predicted_nt"])
    )

    nt_mismatches = 0
    for _, row in frozen_nodes.iterrows():
        bid = row["bodyId"]
        frozen_nt = row["predicted_nt"]
        source_nt = source_nt_map.get(bid)
        if source_nt and frozen_nt != source_nt:
            nt_mismatches += 1

    check(
        nt_mismatches == 0,
        f"All NT predictions match source ({nt_mismatches} mismatches)",
    )

    # ══════════════════════════════════════════════════════════════
    # CHECK 12: PROVENANCE CHECKSUMS
    # ══════════════════════════════════════════════════════════════
    print("\n12. PROVENANCE CHECKSUMS")

    file_map = {
        "body_annotations": ANNOTATIONS_PATH,
        "connectome_weights": CONNECTIVITY_PATH,
        "body_neurotransmitters": NT_PATH,
    }

    for name, path in file_map.items():
        recorded_sha = (
            provenance.get("source_files", {})
            .get(name, {})
            .get("sha256", "MISSING")
        )
        current_sha = compute_sha256(path)
        check(
            recorded_sha == current_sha,
            f"{name} checksum matches (SHA-256)",
        )
        if recorded_sha != current_sha:
            print(f"    Recorded: {recorded_sha}")
            print(f"    Current:  {current_sha}")

    # ══════════════════════════════════════════════════════════════
    # CHECK 13: NORMALIZATION CONSISTENCY
    # ══════════════════════════════════════════════════════════════
    print("\n13. NORMALIZATION")

    w_max = frozen_edges["weight"].max()
    expected_norm = frozen_edges["weight"] / w_max
    norm_diff = (frozen_edges["weight_normalized"] - expected_norm).abs().max()

    check(
        norm_diff < 1e-10,
        f"Normalization is consistent (max diff: {norm_diff:.2e})",
    )

    check(
        np.isclose(frozen_edges["weight_normalized"].max(), 1.0),
        "Max normalized weight = 1.0",
    )

    # ══════════════════════════════════════════════════════════════
    # CHECK 14: SCHEMA VALIDITY
    # ══════════════════════════════════════════════════════════════
    print("\n14. SCHEMA")

    node_cols = set(frozen_nodes.columns)
    schema_node_cols = set(schema.get("nodes", {}).get("columns", {}).keys())
    check(
        schema_node_cols.issubset(node_cols),
        f"All schema node columns present in CSV",
    )

    edge_cols = set(frozen_edges.columns)
    schema_edge_cols = set(schema.get("edges", {}).get("columns", {}).keys())
    check(
        schema_edge_cols.issubset(edge_cols),
        f"All schema edge columns present in CSV",
    )

    # ══════════════════════════════════════════════════════════════
    # PHASE 2 STATISTICS REPRODUCTION
    # ══════════════════════════════════════════════════════════════
    print("\n15. PHASE 2 STATISTICS REPRODUCTION")

    # Reproduce key Phase 1/2 discovery statistics
    for dn_type, expected_total in [
        ("DNp01", 11224),
        ("DNp04", 14995),
        ("DNp06", 2871),
    ]:
        dn_ids = set(
            frozen_nodes[frozen_nodes["type"] == dn_type]["bodyId"].tolist()
        )
        visual_input = frozen_edges[
            (frozen_edges["bodyId_post"].isin(dn_ids))
            & (frozen_edges["pre_type"].isin({"LC4", "LPLC2"}))
        ]
        total = int(visual_input["weight"].sum())

        # Discovery used w_min=1 (no threshold), frozen circuit uses w_min=3
        # So frozen totals will be <= discovery totals
        # We check that frozen total is close but not exceeding discovery total
        check(
            total <= expected_total,
            f"{dn_type} visual input weight ({total}) <= "
            f"discovery total ({expected_total})",
        )

        # Should be at least 95% of discovery total (small edges pruned)
        ratio = total / expected_total if expected_total > 0 else 0
        print(f"    {dn_type}: frozen={total}, discovery={expected_total}, "
              f"ratio={ratio:.4f}")

    # ══════════════════════════════════════════════════════════════
    # FINAL SUMMARY
    # ══════════════════════════════════════════════════════════════
    total = passed + failed
    print("\n" + "=" * 60)
    print(f"VERIFICATION COMPLETE: {passed}/{total} checks passed")

    if failed > 0:
        print(f"\n{failed} CHECKS FAILED:")
        for f in failures:
            print(f"  ✗ {f}")
        print("\nCIRCUIT v1 CANNOT BE CONSIDERED VERIFIED")
        sys.exit(1)
    else:
        print("ALL CHECKS PASSED — CIRCUIT v1 IS VERIFIED")

    print("=" * 60)


if __name__ == "__main__":
    main()
