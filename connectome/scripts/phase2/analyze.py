"""Compute candidate descending neuron metrics, robustness, and pathways from MaleCNS v1.0."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.feather as feather
import pyarrow.ipc as ipc

REPO_ROOT = Path(__file__).resolve().parents[3]
RAW_DATA_DIR = REPO_ROOT / "connectome" / "data" / "raw"
DISCOVERY_DIR = REPO_ROOT / "connectome" / "data" / "discovery"
PHASE2_DIR = REPO_ROOT / "connectome" / "phase2"

ANNOTATIONS_PATH = RAW_DATA_DIR / "annotations" / "body-annotations-male-cns-v1.0-minconf-0.5.feather"
CONNECTIVITY_PATH = RAW_DATA_DIR / "connectivity" / "connectome-weights-male-cns-v1.0-minconf-0.5.feather"
NT_PATH = RAW_DATA_DIR / "neurotransmitters" / "body-neurotransmitters-male-cns-v1.0.feather"

EXPECTED_CHECKSUMS = {
    "body_annotations": "2177e246113e4cfbf1e7772ec37c6da1955ff22e8063d0b1f833101f99a9a3b2",
    "connectome_weights": "e35da783d1c686b2b58b3b87cd6a403ae43bfcfba8bff28e08ef752c1a56afc1",
    "body_neurotransmitters": "95c9289220663abeb3409f3ad9e5a7f8a53f8093f5139d15502cd08da8879621",
}

THRESHOLDS = [1, 3, 10]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def verify_source_checksums():
    print("Checking source dataset checksums...")
    actual_ann = sha256_file(ANNOTATIONS_PATH)
    actual_conn = sha256_file(CONNECTIVITY_PATH)
    actual_nt = sha256_file(NT_PATH)

    assert actual_ann == EXPECTED_CHECKSUMS["body_annotations"], f"Annotations hash mismatch: {actual_ann}"
    assert actual_conn == EXPECTED_CHECKSUMS["connectome_weights"], f"Weights hash mismatch: {actual_conn}"
    assert actual_nt == EXPECTED_CHECKSUMS["body_neurotransmitters"], f"NT hash mismatch: {actual_nt}"
    print("All source dataset checksums verified successfully.")


def parse_soma_location(loc_val):
    if loc_val is None or (isinstance(loc_val, float) and np.isnan(loc_val)):
        return None, None, None
    if isinstance(loc_val, (list, np.ndarray)):
        if len(loc_val) == 3:
            return float(loc_val[0]), float(loc_val[1]), float(loc_val[2])
    if isinstance(loc_val, str):
        # Format like "[67030 31950 27092]" or "67030, 31950, 27092"
        cleaned = loc_val.strip("[]() ")
        parts = re.split(r"[\s,]+", cleaned)
        if len(parts) == 3:
            try:
                return float(parts[0]), float(parts[1]), float(parts[2])
            except ValueError:
                pass
    return None, None, None


def load_metadata():
    print("Loading body annotations...")
    ann_table = feather.read_table(ANNOTATIONS_PATH)
    ann_df = ann_table.to_pandas()

    # Identify LC4 and LPLC2
    lc4_mask = ann_df["type"] == "LC4"
    lplc2_mask = ann_df["type"] == "LPLC2"
    dn_mask = ann_df["superclass"] == "descending_neuron"

    lc4_ids = set(ann_df[lc4_mask]["bodyId"])
    lplc2_ids = set(ann_df[lplc2_mask]["bodyId"])
    dn_ids = set(ann_df[dn_mask]["bodyId"])

    print(f"Found {len(lc4_ids)} LC4, {len(lplc2_ids)} LPLC2, {len(dn_ids)} Descending Neurons.")

    # Null/missing type count in descending neurons
    null_dns = ann_df[dn_mask & ann_df["type"].isna()]["bodyId"].tolist()
    print(f"Descending neurons with null type: {len(null_dns)} ({null_dns})")

    # Parse soma locations
    soma_coords = [parse_soma_location(loc) for loc in ann_df["somaLocation"]]
    ann_df["soma_x"] = [c[0] for c in soma_coords]
    ann_df["soma_y"] = [c[1] for c in soma_coords]
    ann_df["soma_z"] = [c[2] for c in soma_coords]

    type_map = dict(zip(ann_df["bodyId"], ann_df["type"].fillna("UNKNOWN")))
    side_map = dict(zip(ann_df["bodyId"], ann_df["somaSide"].fillna("UNKNOWN")))
    instance_map = dict(zip(ann_df["bodyId"], ann_df["instance"].fillna("")))
    status_map = dict(zip(ann_df["bodyId"], ann_df["status"].fillna("")))
    soma_x_map = dict(zip(ann_df["bodyId"], ann_df["soma_x"]))
    soma_y_map = dict(zip(ann_df["bodyId"], ann_df["soma_y"]))
    soma_z_map = dict(zip(ann_df["bodyId"], ann_df["soma_z"]))

    return {
        "ann_df": ann_df,
        "lc4_ids": lc4_ids,
        "lplc2_ids": lplc2_ids,
        "dn_ids": dn_ids,
        "null_dns": null_dns,
        "type_map": type_map,
        "side_map": side_map,
        "instance_map": instance_map,
        "status_map": status_map,
        "soma_x_map": soma_x_map,
        "soma_y_map": soma_y_map,
        "soma_z_map": soma_z_map,
    }


def load_neurotransmitters():
    print("Loading neurotransmitter predictions...")
    nt_table = feather.read_table(NT_PATH)
    nt_df = nt_table.to_pandas()
    nt_map = {}
    for _, row in nt_df.iterrows():
        nt_map[row["body"]] = {
            "predicted_nt": row.get("predicted_nt"),
            "predicted_nt_confidence": row.get("predicted_nt_confidence"),
            "consensus_nt": row.get("consensus_nt"),
            "total_nt_predictions": row.get("total_nt_predictions"),
        }
    print(f"Loaded neurotransmitter profiles for {len(nt_map):,} neurons.")
    return nt_map


def scan_direct_visual_edges(meta):
    print("Scanning direct visual -> DN edges from connectome...")
    lc4_ids = meta["lc4_ids"]
    lplc2_ids = meta["lplc2_ids"]
    dn_ids = meta["dn_ids"]
    vis_ids = lc4_ids | lplc2_ids

    vis_arr = pa.array(sorted(vis_ids), type=pa.int64())
    dn_arr = pa.array(sorted(dn_ids), type=pa.int64())

    source = pa.memory_map(str(CONNECTIVITY_PATH), "r")
    reader = ipc.open_file(source)

    matching_batches = []
    for i in range(reader.num_record_batches):
        batch = reader.get_batch(i)
        pre = pc.cast(batch["body_pre"], pa.int64(), safe=False)
        post = pc.cast(batch["body_post"], pa.int64(), safe=False)
        mask = pc.and_(pc.is_in(pre, value_set=vis_arr), pc.is_in(post, value_set=dn_arr))
        filtered = batch.filter(mask)
        if len(filtered) > 0:
            matching_batches.append(filtered.to_pandas())

    source.close()

    raw_edges = pd.concat(matching_batches, ignore_index=True)
    # Aggregate duplicate (body_pre, body_post) pairs if present
    agg_edges = (
        raw_edges.groupby(["body_pre", "body_post"], as_index=False)["weight"]
        .sum()
        .sort_values(["weight", "body_post"], ascending=[False, True])
    )

    agg_edges["pre_type"] = agg_edges["body_pre"].map(meta["type_map"])
    agg_edges["pre_side"] = agg_edges["body_pre"].map(meta["side_map"])
    agg_edges["post_type"] = agg_edges["body_post"].map(meta["type_map"])
    agg_edges["post_side"] = agg_edges["body_post"].map(meta["side_map"])
    agg_edges["source_population"] = agg_edges["pre_type"]
    agg_edges["target_population"] = agg_edges["post_type"]
    agg_edges["is_ipsilateral"] = agg_edges["pre_side"] == agg_edges["post_side"]
    agg_edges["survives_w3"] = agg_edges["weight"] >= 3
    agg_edges["survives_w10"] = agg_edges["weight"] >= 10

    agg_edges = agg_edges.rename(
        columns={
            "body_pre": "pre_bodyId",
            "body_post": "post_bodyId",
        }
    )

    cols = [
        "pre_bodyId",
        "pre_type",
        "pre_side",
        "post_bodyId",
        "post_type",
        "post_side",
        "weight",
        "source_population",
        "target_population",
        "is_ipsilateral",
        "survives_w3",
        "survives_w10",
    ]
    agg_edges = agg_edges[cols]

    edge_csv_path = PHASE2_DIR / "direct_visual_dn_edges.csv"
    agg_edges.to_csv(edge_csv_path, index=False)
    print(f"Saved {len(agg_edges)} direct visual -> DN edges to {edge_csv_path.name}")
    return agg_edges


def scan_candidate_total_incoming(candidate_dn_ids):
    print(f"Computing total incoming dendritic inputs for {len(candidate_dn_ids)} candidate DNs across 151M edges...")
    source = pa.memory_map(str(CONNECTIVITY_PATH), "r")
    reader = ipc.open_file(source)

    cand_arr = pa.array(sorted(candidate_dn_ids), type=pa.int64())
    incoming_weight = {b: 0 for b in candidate_dn_ids}
    incoming_edges = {b: 0 for b in candidate_dn_ids}

    for i in range(reader.num_record_batches):
        batch = reader.get_batch(i)
        post = pc.cast(batch["body_post"], pa.int64(), safe=False)
        mask = pc.is_in(post, value_set=cand_arr)
        filtered = batch.filter(mask)
        if len(filtered) > 0:
            df = filtered.to_pandas()
            for b, w in zip(df["body_post"], df["weight"]):
                incoming_weight[b] += int(w)
                incoming_edges[b] += 1

    source.close()
    print("Completed total incoming input scan.")
    return incoming_weight, incoming_edges


def compute_dn_metrics_at_threshold(edges, all_candidate_ids, total_incoming_dict, w_min, meta):
    filtered_edges = edges[edges["weight"] >= w_min]

    rows = []
    for body_id in sorted(all_candidate_ids):
        dn_edges = filtered_edges[filtered_edges["post_bodyId"] == body_id]
        lc4_edges = dn_edges[dn_edges["source_population"] == "LC4"]
        lplc2_edges = dn_edges[dn_edges["source_population"] == "LPLC2"]

        lc4_weight = int(lc4_edges["weight"].sum())
        lplc2_weight = int(lplc2_edges["weight"].sum())
        total_visual_weight = lc4_weight + lplc2_weight

        lc4_presyn_count = int(lc4_edges["pre_bodyId"].nunique())
        lplc2_presyn_count = int(lplc2_edges["pre_bodyId"].nunique())
        direct_visual_partners = lc4_presyn_count + lplc2_presyn_count

        total_in = total_incoming_dict.get(body_id, 0)
        visual_share = (total_visual_weight / total_in) if total_in > 0 else 0.0

        lc4_frac_vis = (lc4_weight / total_visual_weight) if total_visual_weight > 0 else 0.0
        lplc2_frac_vis = (lplc2_weight / total_visual_weight) if total_visual_weight > 0 else 0.0

        ipsi_weight = int(dn_edges[dn_edges["is_ipsilateral"]]["weight"].sum())
        contra_weight = int(dn_edges[~dn_edges["is_ipsilateral"]]["weight"].sum())

        receives_lc4 = lc4_weight > 0
        receives_lplc2 = lplc2_weight > 0
        receives_both = receives_lc4 and receives_lplc2

        rows.append(
            {
                "bodyId": body_id,
                "type": meta["type_map"].get(body_id, "UNKNOWN"),
                "somaSide": meta["side_map"].get(body_id, "UNKNOWN"),
                "instance": meta["instance_map"].get(body_id, ""),
                "status": meta["status_map"].get(body_id, ""),
                f"LC4_weight_w{w_min}": lc4_weight,
                f"LPLC2_weight_w{w_min}": lplc2_weight,
                f"total_visual_weight_w{w_min}": total_visual_weight,
                "total_incoming_weight": total_in,
                f"visual_share_w{w_min}": visual_share,
                f"LC4_fraction_visual_w{w_min}": lc4_frac_vis,
                f"LPLC2_fraction_visual_w{w_min}": lplc2_frac_vis,
                f"LC4_presynaptic_count_w{w_min}": lc4_presyn_count,
                f"LPLC2_presynaptic_count_w{w_min}": lplc2_presyn_count,
                f"direct_visual_partners_w{w_min}": direct_visual_partners,
                f"ipsilateral_visual_weight_w{w_min}": ipsi_weight,
                f"contralateral_visual_weight_w{w_min}": contra_weight,
                f"receives_both_w{w_min}": receives_both,
            }
        )

    df = pd.DataFrame(rows)

    # Calculate ranks (descending order, 1 is highest)
    df[f"rank_total_visual_w{w_min}"] = df[f"total_visual_weight_w{w_min}"].rank(ascending=False, method="min").astype(int)
    df[f"rank_visual_share_w{w_min}"] = df[f"visual_share_w{w_min}"].rank(ascending=False, method="min").astype(int)
    df[f"rank_LC4_w{w_min}"] = df[f"LC4_weight_w{w_min}"].rank(ascending=False, method="min").astype(int)
    df[f"rank_LPLC2_w{w_min}"] = df[f"LPLC2_weight_w{w_min}"].rank(ascending=False, method="min").astype(int)

    return df


def build_candidate_summaries(edges, meta, nt_map):
    all_candidate_ids = set(edges["post_bodyId"].unique())
    print(f"Total candidate descending neurons receiving direct visual input: {len(all_candidate_ids)}")

    total_in_dict, total_edge_dict = scan_candidate_total_incoming(all_candidate_ids)

    df_w1 = compute_dn_metrics_at_threshold(edges, all_candidate_ids, total_in_dict, 1, meta)
    df_w3 = compute_dn_metrics_at_threshold(edges, all_candidate_ids, total_in_dict, 3, meta)
    df_w10 = compute_dn_metrics_at_threshold(edges, all_candidate_ids, total_in_dict, 10, meta)

    # Save per-threshold summaries
    for w_min, df_w in [(1, df_w1), (3, df_w3), (10, df_w10)]:
        clean_df = df_w.copy()
        clean_cols = {}
        for c in clean_df.columns:
            if c.endswith(f"_w{w_min}"):
                clean_cols[c] = c[: -len(f"_w{w_min}")]
        clean_df = clean_df.rename(columns=clean_cols)
        clean_df = clean_df.sort_values(["total_visual_weight", "visual_share"], ascending=[False, False])
        path = PHASE2_DIR / f"candidate_dn_summary_w{w_min}.csv"
        clean_df.to_csv(path, index=False)
        print(f"Saved {len(clean_df)} candidate rows to {path.name}")

    # Master summary table
    master_df = df_w1.copy()
    for col in [c for c in df_w3.columns if f"_w3" in c]:
        master_df[col] = df_w3[col]
    for col in [c for c in df_w10.columns if f"_w10" in c]:
        master_df[col] = df_w10[col]

    master_df["total_incoming_edges"] = master_df["bodyId"].map(total_edge_dict)
    master_df["predicted_nt"] = [nt_map.get(b, {}).get("predicted_nt") for b in master_df["bodyId"]]
    master_df["predicted_nt_confidence"] = [nt_map.get(b, {}).get("predicted_nt_confidence") for b in master_df["bodyId"]]
    master_df["consensus_nt"] = [nt_map.get(b, {}).get("consensus_nt") for b in master_df["bodyId"]]

    master_df = master_df.sort_values(["total_visual_weight_w1", "visual_share_w1"], ascending=[False, False])
    master_path = PHASE2_DIR / "candidate_dn_summary.csv"
    master_df.to_csv(master_path, index=False)
    print(f"Saved unified candidate summary to {master_path.name}")

    return master_df, df_w1, df_w3, df_w10


def build_threshold_robustness(df_w1, df_w3, df_w10):
    print("Building threshold robustness analysis...")
    records = []
    for w, df in [(1, df_w1), (3, df_w3), (10, df_w10)]:
        vis_col = f"total_visual_weight_w{w}"
        lc4_col = f"LC4_weight_w{w}"
        lplc2_col = f"LPLC2_weight_w{w}"
        both_col = f"receives_both_w{w}"

        active = df[df[vis_col] > 0]
        lc4_active = df[df[lc4_col] > 0]
        lplc2_active = df[df[lplc2_col] > 0]
        both_active = df[df[both_col]]

        records.append(
            {
                "threshold": f"w_min >= {w}",
                "w_min": w,
                "total_candidate_count": len(active),
                "lc4_recipient_count": len(lc4_active),
                "lplc2_recipient_count": len(lplc2_active),
                "convergence_both_count": len(both_active),
                "total_visual_synapses": int(df[vis_col].sum()),
                "total_lc4_synapses": int(df[lc4_col].sum()),
                "total_lplc2_synapses": int(df[lplc2_col].sum()),
            }
        )

    summary_df = pd.DataFrame(records)

    # Detailed candidate tracking
    candidate_tracking = []
    for body_id in df_w1["bodyId"]:
        row1 = df_w1[df_w1["bodyId"] == body_id].iloc[0]
        row3 = df_w3[df_w3["bodyId"] == body_id].iloc[0]
        row10 = df_w10[df_w10["bodyId"] == body_id].iloc[0]

        w1_vis = row1["total_visual_weight_w1"]
        w3_vis = row3["total_visual_weight_w3"]
        w10_vis = row10["total_visual_weight_w10"]

        status = "Robust (survives w10)" if w10_vis > 0 else ("Moderate (survives w3)" if w3_vis > 0 else "Weak (w1 only)")

        candidate_tracking.append(
            {
                "bodyId": body_id,
                "type": row1["type"],
                "somaSide": row1["somaSide"],
                "robustness_status": status,
                "weight_w1": w1_vis,
                "weight_w3": w3_vis,
                "weight_w10": w10_vis,
                "retention_rate_w3_to_w1": round(w3_vis / w1_vis, 4) if w1_vis > 0 else 0.0,
                "retention_rate_w10_to_w1": round(w10_vis / w1_vis, 4) if w1_vis > 0 else 0.0,
                "rank_w1": int(row1["rank_total_visual_w1"]),
                "rank_w3": int(row3["rank_total_visual_w3"]) if w3_vis > 0 else None,
                "rank_w10": int(row10["rank_total_visual_w10"]) if w10_vis > 0 else None,
                "receives_both_w1": row1["receives_both_w1"],
                "receives_both_w3": row3["receives_both_w3"],
                "receives_both_w10": row10["receives_both_w10"],
            }
        )

    track_df = pd.DataFrame(candidate_tracking).sort_values("weight_w1", ascending=False)
    out_path = PHASE2_DIR / "threshold_robustness.csv"
    track_df.to_csv(out_path, index=False)
    print(f"Saved threshold robustness table to {out_path.name}")
    return summary_df, track_df


def analyze_two_step_pathways(meta, candidate_dn_ids, nt_map):
    print("Analyzing two-step / intermediate pathways...")
    # Load Phase 1 two-step paths
    p1_two_step_path = DISCOVERY_DIR / "two_step_visual_descending_paths.csv"
    if not p1_two_step_path.exists():
        raise FileNotFoundError(f"Required Phase 1 file missing: {p1_two_step_path}")

    two_step_df = pd.read_csv(p1_two_step_path)
    print(f"Loaded {len(two_step_df):,} two-step path entries from Phase 1 discovery.")

    # Calculate path product and min metrics
    two_step_df["path_product_weight"] = two_step_df["visual_to_intermediate_weight"] * two_step_df["intermediate_to_descending_weight"]
    two_step_df["path_min_weight"] = two_step_df[["visual_to_intermediate_weight", "intermediate_to_descending_weight"]].min(axis=1)
    two_step_df["survives_w3"] = (two_step_df["visual_to_intermediate_weight"] >= 3) & (two_step_df["intermediate_to_descending_weight"] >= 3)
    two_step_df["survives_w10"] = (two_step_df["visual_to_intermediate_weight"] >= 10) & (two_step_df["intermediate_to_descending_weight"] >= 10)

    # Filter paths to candidate DNs
    two_step_cand_df = two_step_df[two_step_df["descending_body"].isin(candidate_dn_ids)].copy()

    two_step_cand_sorted = two_step_cand_df.sort_values("path_product_weight", ascending=False)
    paths_out = PHASE2_DIR / "two_step_paths.csv"
    two_step_cand_sorted.to_csv(paths_out, index=False)
    print(f"Saved {len(two_step_cand_sorted)} two-step paths to candidate DNs to {paths_out.name}")

    # Aggregate by intermediate body
    grouped = two_step_cand_df.groupby("intermediate_body")
    inter_records = []

    # Scan incoming inputs for top intermediates by path weight
    top_inter_bodies = (
        two_step_cand_df.groupby("intermediate_body")["intermediate_to_descending_weight"]
        .sum()
        .sort_values(ascending=False)
        .head(250)
        .index.tolist()
    )

    print(f"Scanning full connectome for incoming inputs of top {len(top_inter_bodies)} intermediate neurons...")
    inter_total_in, _ = scan_candidate_total_incoming(set(top_inter_bodies))

    for inter_id, group in grouped:
        inter_type = meta["type_map"].get(inter_id, "UNKNOWN")
        inter_side = meta["side_map"].get(inter_id, "UNKNOWN")

        lc4_in = int(group[group["source_type"] == "LC4"]["visual_to_intermediate_weight"].drop_duplicates().sum())
        lplc2_in = int(group[group["source_type"] == "LPLC2"]["visual_to_intermediate_weight"].drop_duplicates().sum())
        total_vis_in = lc4_in + lplc2_in

        output_to_cand_dns = int(group.groupby("descending_body")["intermediate_to_descending_weight"].first().sum())
        num_downstream_dns = int(group["descending_body"].nunique())

        total_in = inter_total_in.get(inter_id, 0)
        vis_share = (total_vis_in / total_in) if total_in > 0 else 0.0

        nt_info = nt_map.get(inter_id, {})
        pred_nt = nt_info.get("predicted_nt", "UNKNOWN")
        nt_conf = nt_info.get("predicted_nt_confidence", 0.0)

        path_score = total_vis_in * output_to_cand_dns
        min_path = min(total_vis_in, output_to_cand_dns)

        surv_w3 = (total_vis_in >= 3) and (output_to_cand_dns >= 3)
        surv_w10 = (total_vis_in >= 10) and (output_to_cand_dns >= 10)

        inter_records.append(
            {
                "intermediate_bodyId": inter_id,
                "intermediate_type": inter_type,
                "intermediate_side": inter_side,
                "LC4_input_weight": lc4_in,
                "LPLC2_input_weight": lplc2_in,
                "total_visual_input_weight": total_vis_in,
                "total_incoming_weight": total_in if total_in > 0 else None,
                "visual_input_share": vis_share if total_in > 0 else None,
                "output_weight_to_candidate_dns": output_to_cand_dns,
                "num_downstream_candidate_dns": num_downstream_dns,
                "path_score_product": path_score,
                "min_path_capacity": min_path,
                "predicted_nt": pred_nt,
                "predicted_nt_confidence": nt_conf,
                "survives_w3": surv_w3,
                "survives_w10": surv_w10,
            }
        )

    inter_df = pd.DataFrame(inter_records).sort_values("path_score_product", ascending=False)
    inter_out = PHASE2_DIR / "intermediate_candidates.csv"
    inter_df.to_csv(inter_out, index=False)
    print(f"Saved {len(inter_df)} intermediate candidate summaries to {inter_out.name}")
    return inter_df, two_step_cand_df


def build_retinotopy_proxy(meta, candidate_dn_ids):
    print("Building retinotopy proxy analysis...")
    ann_df = meta["ann_df"]

    # Verify that assignedOlHex columns are empty
    hex1_count = ann_df["assignedOlHex1"].dropna().count()
    hex2_count = ann_df["assignedOlHex2"].dropna().count()
    print(f"Assigned OL Hex non-null counts: Hex1={hex1_count}, Hex2={hex2_count}")

    # Extract 3D soma coordinates for LC4, LPLC2, and candidate DNs
    lc4_mask = ann_df["type"] == "LC4"
    lplc2_mask = ann_df["type"] == "LPLC2"
    cand_dn_mask = ann_df["bodyId"].isin(candidate_dn_ids)

    sub_df = ann_df[lc4_mask | lplc2_mask | cand_dn_mask].copy()

    records = []
    for _, row in sub_df.iterrows():
        b_id = row["bodyId"]
        t = row["type"]
        s = row["somaSide"]
        x, y, z = row["soma_x"], row["soma_y"], row["soma_z"]
        role = "visual_projection" if t in ["LC4", "LPLC2"] else "candidate_descending"
        records.append(
            {
                "bodyId": b_id,
                "type": t if pd.notna(t) else "UNKNOWN",
                "role": role,
                "somaSide": s,
                "soma_x": x,
                "soma_y": y,
                "soma_z": z,
                "retinotopic_column_available": False,
                "coordinate_type": "soma_centroid_nm",
            }
        )

    ret_df = pd.DataFrame(records)
    ret_path = PHASE2_DIR / "retinotopy_proxy.csv"
    ret_df.to_csv(ret_path, index=False)
    print(f"Saved retinotopy proxy ({len(ret_df)} neurons) to {ret_path.name}")
    return ret_df


def build_neurotransmitter_analysis(meta, candidate_dn_ids, inter_df, nt_map):
    print("Building neurotransmitter analysis table...")
    # Include all LC4 (126), LPLC2 (185), 63 candidate DNs, and top 50 intermediates
    lc4_ids = sorted(meta["lc4_ids"])
    lplc2_ids = sorted(meta["lplc2_ids"])
    dn_ids = sorted(candidate_dn_ids)
    top_inter_ids = inter_df.head(50)["intermediate_bodyId"].tolist()

    all_bodies = []
    for b in lc4_ids:
        all_bodies.append((b, "LC4", "visual_projection_input"))
    for b in lplc2_ids:
        all_bodies.append((b, "LPLC2", "visual_projection_input"))
    for b in dn_ids:
        all_bodies.append((b, meta["type_map"].get(b, "UNKNOWN"), "candidate_descending_readout"))
    for b in top_inter_ids:
        all_bodies.append((b, meta["type_map"].get(b, "UNKNOWN"), "candidate_intermediate_interneuron"))

    records = []
    for b, t, role in all_bodies:
        nt_info = nt_map.get(b, {})
        pred_nt = nt_info.get("predicted_nt", "UNKNOWN")
        conf = nt_info.get("predicted_nt_confidence")
        cons_nt = nt_info.get("consensus_nt", "UNKNOWN")
        tot_pred = nt_info.get("total_nt_predictions")

        # Functional sign justification: False in all cases because predicted NT does not specify receptor subtype
        records.append(
            {
                "bodyId": b,
                "type": t,
                "side": meta["side_map"].get(b, "UNKNOWN"),
                "circuit_role": role,
                "predicted_nt": pred_nt,
                "predicted_nt_confidence": conf,
                "consensus_nt": cons_nt,
                "total_predictions": tot_pred,
                "functional_sign_justified": False,
                "functional_sign_limitation": (
                    "Receptor identity unmapped; cholinergic synapses can act via muscarinic receptors (inhibitory) "
                    "or nicotinic receptors (excitatory); glutamatergic transmission can be inhibitory via GluCl "
                    "or excitatory via AMPA-like receptors. Unsigned weights maintained."
                ),
            }
        )

    nt_out_df = pd.DataFrame(records)
    nt_path = PHASE2_DIR / "neurotransmitter_analysis.csv"
    nt_out_df.to_csv(nt_path, index=False)
    print(f"Saved neurotransmitter analysis ({len(nt_out_df)} rows) to {nt_path.name}")
    return nt_out_df


def generate_provenance(meta, candidate_dn_ids):
    print("Generating Phase 2 provenance metadata...")
    prov = {
        "phase": "Phase 2: Candidate Circuit Analysis & Biological Validation",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "script": "connectome/scripts/phase2/analyze.py",
        "dataset": {
            "name": "MaleCNS v1.0",
            "identifier": "male-cns:v1.0",
            "server": "https://neuprint.janelia.org",
        },
        "source_files": {
            "body_annotations": {
                "filename": ANNOTATIONS_PATH.name,
                "path": str(ANNOTATIONS_PATH.relative_to(REPO_ROOT)),
                "sha256": EXPECTED_CHECKSUMS["body_annotations"],
                "total_rows": len(meta["ann_df"]),
            },
            "connectome_weights": {
                "filename": CONNECTIVITY_PATH.name,
                "path": str(CONNECTIVITY_PATH.relative_to(REPO_ROOT)),
                "sha256": EXPECTED_CHECKSUMS["connectome_weights"],
                "total_rows": 151856684,
            },
            "body_neurotransmitters": {
                "filename": NT_PATH.name,
                "path": str(NT_PATH.relative_to(REPO_ROOT)),
                "sha256": EXPECTED_CHECKSUMS["body_neurotransmitters"],
            },
        },
        "thresholds_evaluated": THRESHOLDS,
        "parameters": {
            "aggregation": "sum duplicate (pre, post) pairs",
            "visual_types": ["LC4", "LPLC2"],
            "descending_superclass": "descending_neuron",
            "direct_candidate_dn_count": len(candidate_dn_ids),
        },
        "software": {
            "python": sys.version.split()[0],
            "pandas": pd.__version__,
            "pyarrow": pa.__version__,
            "numpy": np.__version__,
        },
    }

    prov_path = PHASE2_DIR / "phase2_provenance.json"
    with open(prov_path, "w") as f:
        json.dump(prov, f, indent=2)
    print(f"Saved provenance to {prov_path.name}")


def main():
    t0 = time.time()
    print("=" * 60)
    print("FLY — Executing Phase 2 Analysis Pipeline")
    print("=" * 60)

    PHASE2_DIR.mkdir(parents=True, exist_ok=True)

    verify_source_checksums()
    meta = load_metadata()
    nt_map = load_neurotransmitters()

    direct_edges = scan_direct_visual_edges(meta)
    master_df, df_w1, df_w3, df_w10 = build_candidate_summaries(direct_edges, meta, nt_map)

    summary_df, track_df = build_threshold_robustness(df_w1, df_w3, df_w10)
    cand_dn_ids = set(master_df["bodyId"])

    inter_df, two_step_df = analyze_two_step_pathways(meta, cand_dn_ids, nt_map)
    ret_df = build_retinotopy_proxy(meta, cand_dn_ids)
    nt_out_df = build_neurotransmitter_analysis(meta, cand_dn_ids, inter_df, nt_map)

    generate_provenance(meta, cand_dn_ids)

    print("=" * 60)
    print(f"Phase 2 analysis completed successfully in {time.time() - t0:.2f} seconds.")
    print("=" * 60)


if __name__ == "__main__":
    main()
