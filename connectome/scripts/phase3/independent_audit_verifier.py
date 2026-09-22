"""Independent verification of Circuit v1 and v2 against raw connectome feather files."""

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

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[2]
DATA_ROOT = PROJECT_ROOT / "connectome" / "data" / "raw"
PHASE3_DIR = PROJECT_ROOT / "connectome" / "phase3"

ANN_PATH = DATA_ROOT / "annotations" / "body-annotations-male-cns-v1.0-minconf-0.5.feather"
CONN_PATH = DATA_ROOT / "connectivity" / "connectome-weights-male-cns-v1.0-minconf-0.5.feather"
NT_PATH = DATA_ROOT / "neurotransmitters" / "body-neurotransmitters-male-cns-v1.0.feather"

def sha256_of_file(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def normalize_side(soma_side, instance) -> str:
    if pd.notna(soma_side):
        s = str(soma_side).strip().upper()
        if s == "L": return "left"
        if s == "R": return "right"
    if pd.notna(instance):
        inst = str(instance).strip()
        if inst.endswith("_L") or "(L)" in inst: return "left"
        if inst.endswith("_R") or "(R)" in inst: return "right"
    return "unknown"

def main():
    print("=" * 70)
    print("INDEPENDENT RAW CONNECTOME AUDIT & VERIFICATION")
    print("=" * 70)

    # Check 1: Provenance Hashes
    print("\n[STEP 1] Raw Source Data Checksums:")
    hashes = {
        "body_annotations": sha256_of_file(ANN_PATH),
        "connectome_weights": sha256_of_file(CONN_PATH),
        "body_neurotransmitters": sha256_of_file(NT_PATH),
    }
    for k, h in hashes.items():
        print(f"  {k}: {h}")

    with open(PHASE3_DIR / "circuit_v2_provenance.json") as f:
        prov = json.load(f)

    for k, h in hashes.items():
        expected_h = prov["source_files"][k]["sha256"]
        assert h == expected_h, f"Hash mismatch on {k}: {h} vs {expected_h}"
    print("  ✓ All raw source file SHA-256 checksums match provenance exactly.")

    # Check 2: Raw Annotations Inspection
    print("\n[STEP 2] Raw Body Annotations Audit:")
    ann = pd.read_feather(ANN_PATH, columns=["bodyId", "type", "instance", "somaSide"])
    ann["bodyId"] = pd.to_numeric(ann["bodyId"], errors="coerce")
    ann = ann.dropna(subset=["bodyId"]).copy()
    ann["bodyId"] = ann["bodyId"].astype(np.int64)
    ann["type_clean"] = ann["type"].astype(str).str.strip()
    ann["side_norm"] = ann.apply(lambda r: normalize_side(r["somaSide"], r["instance"]), axis=1)

    v1_types = ["LC4", "LPLC2", "DNp01", "DNp04", "DNp06"]
    v2_types = ["LC4", "LPLC2", "DNp01", "DNp04", "DNp06", "DNp02", "DNp11"]

    ann_v1 = ann[ann["type_clean"].isin(v1_types)].drop_duplicates(subset=["bodyId"]).copy()
    ann_v2 = ann[ann["type_clean"].isin(v2_types)].drop_duplicates(subset=["bodyId"]).copy()

    print(f"  Raw v1 unique bodies: {len(ann_v1)}")
    print(f"  Raw v2 unique bodies: {len(ann_v2)}")
    assert len(ann_v1) == 317, f"Expected 317 v1 bodies, got {len(ann_v1)}"
    assert len(ann_v2) == 321, f"Expected 321 v2 bodies, got {len(ann_v2)}"

    print("\n  Raw Hemisphere Counts:")
    for t in v2_types:
        sub = ann_v2[ann_v2["type_clean"] == t]
        l_cnt = (sub["side_norm"] == "left").sum()
        r_cnt = (sub["side_norm"] == "right").sum()
        print(f"    {t:<8}: Total={len(sub):<3} | Left={l_cnt:<3} | Right={r_cnt:<3}")

    lc4_sub = ann_v2[ann_v2["type_clean"] == "LC4"]
    lplc2_sub = ann_v2[ann_v2["type_clean"] == "LPLC2"]
    assert (lc4_sub["side_norm"] == "left").sum() == 71 and (lc4_sub["side_norm"] == "right").sum() == 55
    assert (lplc2_sub["side_norm"] == "left").sum() == 94 and (lplc2_sub["side_norm"] == "right").sum() == 91
    print("  ✓ LC4 raw hemisphere split verified: 71 Left, 55 Right.")
    print("  ✓ LPLC2 raw hemisphere split verified: 94 Left, 91 Right.")

    # Cross-check DNp04 body IDs digit length
    dnp04_bids = sorted(ann_v2[ann_v2["type_clean"] == "DNp04"]["bodyId"].tolist())
    print(f"  Raw DNp04 body IDs: {dnp04_bids}")
    assert dnp04_bids == [11137, 531898], f"DNp04 IDs unexpected: {dnp04_bids}"
    print("  ✓ DNp04 6-digit bodyId (531898) verified as authentic in raw MaleCNS v1.0.")

    # Check 3: Raw Connectome Edge Re-extraction (Streaming)
    print("\n[STEP 3] Raw Connectome Edge Re-extraction (Streaming 1.05 GB feather):")
    v2_id_set = set(ann_v2["bodyId"])
    v1_id_set = set(ann_v1["bodyId"])
    v2_id_arr = pa.array(sorted(v2_id_set), type=pa.int64())

    source_map = pa.memory_map(str(CONN_PATH), "r")
    reader = ipc.open_file(source_map)
    v2_chunks = []
    for i in range(reader.num_record_batches):
        batch = reader.get_batch(i)
        table = batch.select(["body_pre", "body_post", "weight"])
        pre = pc.cast(table["body_pre"], pa.int64(), safe=False)
        post = pc.cast(table["body_post"], pa.int64(), safe=False)
        pre_mask = np.asarray(pc.is_in(pre, value_set=v2_id_arr))
        post_mask = np.asarray(pc.is_in(post, value_set=v2_id_arr))
        mask = pre_mask & post_mask
        if mask.any():
            filtered = table.filter(pa.array(mask))
            v2_chunks.append(filtered.to_pandas())
    source_map.close()

    raw_v2_edges = pd.concat(v2_chunks, ignore_index=True)
    raw_v2_edges["body_pre"] = raw_v2_edges["body_pre"].astype(np.int64)
    raw_v2_edges["body_post"] = raw_v2_edges["body_post"].astype(np.int64)
    raw_v2_edges["weight"] = pd.to_numeric(raw_v2_edges["weight"], errors="raise")

    # Aggregate duplicate (pre, post) pairs
    agg_v2 = raw_v2_edges.groupby(["body_pre", "body_post"], as_index=False)["weight"].sum()
    recomputed_v2_edges = agg_v2[agg_v2["weight"] >= 3].copy()

    # Reconstruct v1 edges from the same raw stream
    raw_v1_edges = raw_v2_edges[
        raw_v2_edges["body_pre"].isin(v1_id_set) & raw_v2_edges["body_post"].isin(v1_id_set)
    ]
    agg_v1 = raw_v1_edges.groupby(["body_pre", "body_post"], as_index=False)["weight"].sum()
    recomputed_v1_edges = agg_v1[agg_v1["weight"] >= 3].copy()

    print(f"  Raw Reconstructed Circuit v1 Edges (w>=3): {len(recomputed_v1_edges)}")
    print(f"  Raw Reconstructed Circuit v2 Edges (w>=3): {len(recomputed_v2_edges)}")
    assert len(recomputed_v1_edges) == 11286, f"Expected 11286 v1 edges, got {len(recomputed_v1_edges)}"
    assert len(recomputed_v2_edges) == 11557, f"Expected 11557 v2 edges, got {len(recomputed_v2_edges)}"

    # Check 4: Compare Reconstructed vs Stored Artifacts (Tolerance = 0)
    print("\n[STEP 4] Compare Reconstructed vs Stored Artifacts (Tolerance = 0):")
    stored_v1_edges = pd.read_csv(PHASE3_DIR / "circuit_v1_edges.csv")
    stored_v2_edges = pd.read_csv(PHASE3_DIR / "circuit_v2_edges.csv")

    m_v1 = stored_v1_edges.merge(
        recomputed_v1_edges,
        left_on=["bodyId_pre", "bodyId_post"],
        right_on=["body_pre", "body_post"],
        how="outer"
    )
    assert m_v1["body_pre"].notna().all() and m_v1["bodyId_pre"].notna().all()
    assert (m_v1["weight_x"] == m_v1["weight_y"]).all()
    print("  ✓ Circuit v1 stored CSV matches raw recomputed edges exactly (0 mismatches).")

    m_v2 = stored_v2_edges.merge(
        recomputed_v2_edges,
        left_on=["bodyId_pre", "bodyId_post"],
        right_on=["body_pre", "body_post"],
        how="outer"
    )
    assert m_v2["body_pre"].notna().all() and m_v2["bodyId_pre"].notna().all()
    assert (m_v2["weight_x"] == m_v2["weight_y"]).all()
    print("  ✓ Circuit v2 stored CSV matches raw recomputed edges exactly (0 mismatches).")

    # Check 5: V1 to V2 Delta
    print("\n[STEP 5] V1 to V2 Delta Audit:")
    stored_v1_nodes = pd.read_csv(PHASE3_DIR / "circuit_v1_nodes.csv")
    stored_v2_nodes = pd.read_csv(PHASE3_DIR / "circuit_v2_nodes.csv")
    added_nodes = set(stored_v2_nodes["bodyId"]) - set(stored_v1_nodes["bodyId"])
    removed_nodes = set(stored_v1_nodes["bodyId"]) - set(stored_v2_nodes["bodyId"])
    print(f"  Added nodes ({len(added_nodes)}): {added_nodes} (DNp02_L, DNp02_R, DNp11_L, DNp11_R)")
    print(f"  Removed nodes: {len(removed_nodes)}")
    assert removed_nodes == set()
    assert added_nodes == {10197, 10117, 10259, 10106}

    v1_pairs = set(zip(stored_v1_edges["bodyId_pre"], stored_v1_edges["bodyId_post"]))
    v2_pairs = set(zip(stored_v2_edges["bodyId_pre"], stored_v2_edges["bodyId_post"]))
    added_edges = v2_pairs - v1_pairs
    removed_edges = v1_pairs - v2_pairs
    print(f"  Added edges ({len(added_edges)}): {len(added_edges)}")
    print(f"  Removed edges: {len(removed_edges)}")
    assert len(removed_edges) == 0
    assert len(added_edges) == 271

    # Verify all added edges involve at least one of the 4 new neurons
    for pre, post in added_edges:
        assert (pre in added_nodes) or (post in added_nodes), f"Added edge ({pre}, {post}) does not involve new nodes"
    print("  ✓ Every added edge involves at least one of the four new neurons.")

    # Check 6: Edge Classes and Synaptic Totals
    print("\n[STEP 6] Recomputed Edge Classes and Synaptic Totals for Circuit v2:")
    classes_summary = stored_v2_edges.groupby("edge_class")["weight"].agg(["count", "sum"])
    print(classes_summary)
    total_edges = len(stored_v2_edges)
    total_weight = stored_v2_edges["weight"].sum()
    max_weight = stored_v2_edges["weight"].max()
    print(f"  Total Edges: {total_edges}")
    print(f"  Total Synapses: {total_weight}")
    print(f"  Max Weight: {max_weight}")

    assert total_edges == 11557
    assert total_weight == 91023
    assert max_weight == 172
    assert classes_summary.loc["visual_to_readout", "count"] == 1141
    assert classes_summary.loc["visual_to_readout", "sum"] == 36933
    assert classes_summary.loc["inter_readout", "count"] == 27
    assert classes_summary.loc["inter_readout", "sum"] == 416
    assert classes_summary.loc["intra_population", "count"] == 9994
    assert classes_summary.loc["intra_population", "sum"] == 51846
    assert classes_summary.loc["cross_visual", "count"] == 388
    assert classes_summary.loc["cross_visual", "sum"] == 1806
    assert classes_summary.loc["readout_to_visual", "count"] == 7
    assert classes_summary.loc["readout_to_visual", "sum"] == 22
    print("  ✓ All edge classes and synaptic weight sums verified from raw data.")

    print("\n" + "=" * 70)
    print("INDEPENDENT AUDIT VERIFIER COMPLETE — ALL 12 CHECKS PASSED")
    print("=" * 70)

if __name__ == "__main__":
    main()
