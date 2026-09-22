"""
verify_circuit.py — Comprehensive Phase 1 Verification

Validates ALL Phase 1 connectome artifacts for internal consistency,
correctness, and completeness.  Fails loudly (AssertionError) on any
invariant violation.

Checks performed:
  1.  Dataset configuration matches male-cns:v1.0
  2.  Expected neuron populations exist (LC4, LPLC2, DNp01, DNp06)
  3.  DNp01 left and right exist
  4.  No duplicate body IDs
  5.  Node count == matrix dimension
  6.  Matrix index consistency (bijective mapping)
  7.  No NaN / Inf in matrix
  8.  W[post, pre] orientation verified against processed edges
  9.  Every nonzero matrix entry == aggregated edge weight
  10. DNp01 incoming connection summary (left/right, top cell types)
  11. Hemispheric symmetry (informational)
  12. Normalization artifact exists and is valid
  13. Retinotopy status report
  14. Spectral radius (informational)
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


def main():
    ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent   # project root
    BASE_DIR = Path(__file__).resolve().parent.parent.parent           # connectome/
    DATA_DIR = BASE_DIR / "data" / "phase1"

    passed = 0
    total  = 0

    def check(condition, label):
        """Assert with tracking."""
        nonlocal passed, total
        total += 1
        assert condition, f"FAIL: {label}"
        passed += 1
        print(f"  ✓ {label}")

    # ── Load config ─────────────────────────────────────────────────
    config_path = ROOT_DIR / "config.yaml"
    check(config_path.exists(), "config.yaml exists")
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)

    # ── Load all artifacts ──────────────────────────────────────────
    nodes_path  = DATA_DIR / "nodes.csv"
    edges_path  = DATA_DIR / "processed_edges.csv"
    matrix_path = DATA_DIR / "weight_matrix.npy"
    norm_path   = DATA_DIR / "weight_matrix_normalized.npy"
    index_path  = DATA_DIR / "matrix_index.json"

    for p in [nodes_path, edges_path, matrix_path, index_path]:
        check(p.exists(), f"{p.name} exists")

    nodes_df = pd.read_csv(nodes_path)
    edges_df = pd.read_csv(edges_path)
    W        = np.load(matrix_path)
    with open(index_path, "r") as f:
        node_map = json.load(f)

    print("\n" + "=" * 60)
    print("CIRCUIT TOPOLOGY VERIFICATION")
    print("=" * 60)

    # ════════════════════════════════════════════════════════════════
    # 1. DATASET CONFIGURATION
    # ════════════════════════════════════════════════════════════════
    print("\n1. DATASET CONFIGURATION")
    check(
        cfg["dataset"]["name"] == "male-cns:v1.0",
        f"Dataset is male-cns:v1.0 (got: {cfg['dataset']['name']})"
    )

    # ════════════════════════════════════════════════════════════════
    # 2. NEURON POPULATIONS
    # ════════════════════════════════════════════════════════════════
    print("\n2. NEURON POPULATIONS")
    types_present = set(nodes_df["type"].unique())
    for t in ["LC4", "LPLC2", "DNp01", "DNp06"]:
        check(t in types_present, f"{t} population exists")

    type_counts = nodes_df["type"].value_counts()
    for t in ["LC4", "LPLC2", "DNp01", "DNp06"]:
        print(f"     {t}: {type_counts.get(t, 0)} neurons")

    # ════════════════════════════════════════════════════════════════
    # 3. DNp01 LEFT / RIGHT
    # ════════════════════════════════════════════════════════════════
    print("\n3. DNp01 VALIDATION")
    dnp01 = nodes_df[nodes_df["type"] == "DNp01"]
    dnp01_sides = set(dnp01["side"].unique())
    check("left" in dnp01_sides,  "DNp01 left hemisphere neuron exists")
    check("right" in dnp01_sides, "DNp01 right hemisphere neuron exists")

    # ════════════════════════════════════════════════════════════════
    # 4. NO DUPLICATE BODY IDs
    # ════════════════════════════════════════════════════════════════
    print("\n4. DUPLICATE BODY ID CHECK")
    check(
        nodes_df["bodyId"].is_unique,
        f"No duplicate bodyIds in nodes.csv ({len(nodes_df)} unique out of {len(nodes_df)})"
    )

    # ════════════════════════════════════════════════════════════════
    # 5. NODE COUNT == MATRIX DIMENSIONS
    # ════════════════════════════════════════════════════════════════
    print("\n5. DIMENSION CONSISTENCY")
    n_nodes = len(nodes_df)
    check(W.ndim == 2,               f"Matrix is 2-dimensional (ndim={W.ndim})")
    check(W.shape[0] == W.shape[1],  f"Matrix is square ({W.shape})")
    check(W.shape[0] == n_nodes,     f"Matrix dim ({W.shape[0]}) == node count ({n_nodes})")

    # ════════════════════════════════════════════════════════════════
    # 6. MATRIX INDEX CONSISTENCY
    # ════════════════════════════════════════════════════════════════
    print("\n6. MATRIX INDEX CONSISTENCY")
    check(
        len(node_map) == n_nodes,
        f"matrix_index.json entries ({len(node_map)}) == node count ({n_nodes})"
    )

    # Every bodyId in nodes.csv appears exactly once in the index
    node_body_ids  = set(nodes_df["bodyId"].tolist())
    index_body_ids = set(v["bodyId"] for v in node_map.values())
    check(
        node_body_ids == index_body_ids,
        "matrix_index bodyIds == nodes.csv bodyIds (same set)"
    )

    # Index keys are contiguous 0..N-1
    index_keys = sorted(int(k) for k in node_map.keys())
    check(
        index_keys == list(range(n_nodes)),
        f"matrix_index keys are contiguous 0..{n_nodes - 1}"
    )

    # Verify ordering: index position i maps to the i-th row of nodes_df
    node_ids_ordered = nodes_df["bodyId"].tolist()
    for i in range(n_nodes):
        assert node_map[str(i)]["bodyId"] == node_ids_ordered[i], (
            f"matrix_index[{i}] bodyId ({node_map[str(i)]['bodyId']}) "
            f"!= nodes_df row {i} bodyId ({node_ids_ordered[i]})"
        )
    check(True, "matrix_index ordering matches nodes.csv row order")

    # ════════════════════════════════════════════════════════════════
    # 7. MATRIX SANITY
    # ════════════════════════════════════════════════════════════════
    print("\n7. MATRIX SANITY")
    check(not np.isnan(W).any(), "No NaN values in weight matrix")
    check(not np.isinf(W).any(), "No Inf values in weight matrix")
    check((W >= 0).all(),        "All matrix entries are non-negative (unsigned structural weights)")

    # ════════════════════════════════════════════════════════════════
    # 8. W[post, pre] ORIENTATION SPOT-CHECK
    # ════════════════════════════════════════════════════════════════
    print("\n8. W[post, pre] ORIENTATION")
    id_to_idx = {bid: i for i, bid in enumerate(node_ids_ordered)}

    # Pick up to 5 edges and verify orientation
    sample_edges = edges_df.head(min(5, len(edges_df)))
    orientation_ok = True
    for _, row in sample_edges.iterrows():
        pre_idx  = id_to_idx[row["bodyId_pre"]]
        post_idx = id_to_idx[row["bodyId_post"]]
        expected = row["weight"]
        actual   = W[post_idx, pre_idx]
        if actual != expected:
            orientation_ok = False
            print(f"  ✗ W[{post_idx},{pre_idx}] = {actual}, expected {expected}")
    check(orientation_ok, "W[post, pre] orientation verified on sample edges")

    # ════════════════════════════════════════════════════════════════
    # 9. EVERY MATRIX ENTRY == AGGREGATED EDGE WEIGHT
    # ════════════════════════════════════════════════════════════════
    print("\n9. FULL MATRIX ↔ EDGE AGREEMENT")

    # Build a reference matrix from processed edges
    W_ref = np.zeros_like(W)
    for _, row in edges_df.iterrows():
        pre_idx  = id_to_idx.get(row["bodyId_pre"])
        post_idx = id_to_idx.get(row["bodyId_post"])
        if pre_idx is not None and post_idx is not None:
            W_ref[post_idx, pre_idx] = row["weight"]

    check(
        np.array_equal(W, W_ref),
        f"Weight matrix exactly matches edge-reconstructed matrix "
        f"(nonzero: {np.count_nonzero(W)})"
    )

    # Also verify no duplicate (pre,post) pairs in processed_edges
    dup_check = edges_df.groupby(["bodyId_pre", "bodyId_post"]).size()
    check(
        (dup_check == 1).all(),
        f"No duplicate (pre,post) pairs in processed_edges.csv "
        f"({len(dup_check)} unique pairs)"
    )

    # ════════════════════════════════════════════════════════════════
    # 10. DNp01 INCOMING CONNECTIONS
    # ════════════════════════════════════════════════════════════════
    print("\n10. DNp01 INCOMING CONNECTION SUMMARY")

    for side in ["left", "right"]:
        dnp01_side = dnp01[dnp01["side"] == side]
        if dnp01_side.empty:
            continue
        dnp01_body = dnp01_side["bodyId"].iloc[0]
        dnp01_idx  = id_to_idx[dnp01_body]

        incoming = W[dnp01_idx, :]
        total_incoming = incoming.sum()
        print(f"\n   DNp01 {side} (bodyId={dnp01_body}):")
        print(f"     Total incoming synaptic weight: {total_incoming:.0f}")

        # Connections exist
        check(
            total_incoming > 0,
            f"DNp01 {side} has incoming connections (weight={total_incoming:.0f})"
        )

        # Top incoming cell types by summed weight
        incoming_edges = edges_df[edges_df["bodyId_post"] == dnp01_body]
        if not incoming_edges.empty:
            top_types = (
                incoming_edges
                .groupby("pre_type")["weight"]
                .sum()
                .sort_values(ascending=False)
            )
            print(f"     Top incoming cell types:")
            for cell_type, w in top_types.items():
                print(f"       {cell_type}: {w} synapses")

    # ════════════════════════════════════════════════════════════════
    # 11. HEMISPHERIC SYMMETRY (informational)
    # ════════════════════════════════════════════════════════════════
    print("\n11. HEMISPHERIC SYMMETRY (Inputs to DNs)")

    # Build node metadata DataFrame from matrix index
    df_nodes = pd.DataFrame([
        {"idx": int(k), **v} for k, v in node_map.items()
    ]).set_index("idx")

    sensory_indices = df_nodes[df_nodes["type"].isin(["LC4", "LPLC2"])].index.values
    motor_indices   = df_nodes[df_nodes["type"].str.startswith("DN")].index.values

    for dn_idx in motor_indices:
        dn = df_nodes.loc[dn_idx]
        dn_name = f"{dn['type']} ({dn['side']})"
        inputs = W[dn_idx, sensory_indices]

        left_mask  = df_nodes.loc[sensory_indices, "side"] == "left"
        right_mask = df_nodes.loc[sensory_indices, "side"] == "right"

        left_sum  = inputs[left_mask.values].sum()
        right_sum = inputs[right_mask.values].sum()

        print(f"   Target {dn_name}:")
        print(f"      <- Left Hemisphere Synapses:  {left_sum:.0f}")
        print(f"      <- Right Hemisphere Synapses: {right_sum:.0f}")

    # ════════════════════════════════════════════════════════════════
    # 12. NORMALIZATION
    # ════════════════════════════════════════════════════════════════
    print("\n12. NORMALIZATION")
    check(norm_path.exists(), "weight_matrix_normalized.npy exists")
    W_norm = np.load(norm_path)
    check(W_norm.shape == W.shape, f"Normalized matrix shape matches raw ({W_norm.shape})")
    check(not np.isnan(W_norm).any(), "No NaN in normalized matrix")
    check(not np.isinf(W_norm).any(), "No Inf in normalized matrix")

    w_max = W.max()
    if w_max > 0:
        W_norm_expected = W / w_max
        check(
            np.allclose(W_norm, W_norm_expected),
            f"Normalized matrix == raw / max (max={w_max})"
        )
        print(f"     Range: [{W_norm.min():.6f}, {W_norm.max():.6f}]")
        print(f"     Mean:  {W_norm.mean():.6f}")
        print(f"     Std:   {W_norm.std():.6f}")

    # ════════════════════════════════════════════════════════════════
    # 13. RETINOTOPY STATUS
    # ════════════════════════════════════════════════════════════════
    print("\n13. RETINOTOPY / VISUAL METADATA STATUS")
    print("   The MaleCNS v1.0 dataset does NOT populate retinotopic")
    print("   metadata (assignedOlHex1, assignedOlHex2) for LC4/LPLC2")
    print("   neurons — all values are null.")
    print("   ROI data contains lobula column identifiers (e.g.,")
    print("   LO_L_col_18_20) which could serve as retinotopic proxies,")
    print("   but interpreting these requires additional analysis.")
    print("   STATUS: PENDING — no fabricated data included.")

    # ════════════════════════════════════════════════════════════════
    # 14. NETWORK FLOW & SPECTRAL RADIUS (informational)
    # ════════════════════════════════════════════════════════════════
    print("\n14. NETWORK FLOW")
    W_sensory     = W[np.ix_(sensory_indices, sensory_indices)]
    W_feedforward = W[np.ix_(motor_indices, sensory_indices)]
    print(f"   Recurrent synapses (Sensory<->Sensory):  {W_sensory.sum():.0f}")
    print(f"   Feedforward synapses (Sensory->Motor):   {W_feedforward.sum():.0f}")

    print("\n15. SPECTRAL RADIUS (descriptive statistics)")
    eigenvalues_raw = np.linalg.eigvals(W)
    radius_raw = np.max(np.abs(eigenvalues_raw))
    print(f"   Raw matrix      lambda_max: {radius_raw:.4f}")

    eigenvalues_norm = np.linalg.eigvals(W_norm)
    radius_norm = np.max(np.abs(eigenvalues_norm))
    print(f"   Normalized matrix lambda_max: {radius_norm:.4f}")

    print("   Note: These are descriptive statistics of the structural")
    print("   connectivity matrices only. Dynamical stability analysis")
    print("   is deferred to Phase 4, where leaky-integrator time")
    print("   constants, gain, and activation bounds will be defined.")

    # ════════════════════════════════════════════════════════════════
    # FINAL SUMMARY
    # ════════════════════════════════════════════════════════════════
    print("\n" + "=" * 60)
    print(f"VERIFICATION COMPLETE: {passed}/{total} checks passed")
    print("=" * 60)

    # ── Acceptance test summary ─────────────────────────────────────
    print(f"\n  1.  Node count:               {n_nodes}")
    print(f"  2.  Matrix shape:             {W.shape}")
    print(f"  3.  Unique directed edges:    {len(edges_df)}")
    n_raw = None
    raw_path = DATA_DIR / "raw_edges.csv"
    if raw_path.exists():
        raw_df = pd.read_csv(raw_path)
        raw_pairs = raw_df.groupby(["bodyId_pre", "bodyId_post"]).ngroups
        n_raw = len(raw_df)
        # Count how many raw edges (after threshold) mapped to dup pairs
        raw_above = raw_df[raw_df["weight"] >= cfg["processing"]["weight_threshold"]]
        raw_above_pairs = raw_above.groupby(["bodyId_pre", "bodyId_post"]).ngroups
        dup_before_agg = len(raw_above) - raw_above_pairs
        print(f"  4.  Duplicate pre/post pairs: {dup_before_agg} rows "
              f"(before aggregation)")
    print(f"  5.  Total raw synaptic weight: "
          f"{raw_df['weight'].sum() if n_raw else 'N/A'}")
    print(f"  6.  Total aggregated weight:  {edges_df['weight'].sum()} "
          f"(after threshold + aggregation)")
    print(f"  7.  DNp01 L/R incoming:       see section 10 above")
    print(f"  8.  Top incoming to DNp01:    see section 10 above")
    print(f"  9.  Normalization:            method={cfg['normalization']['method']}, "
          f"max={w_max}, range=[{W_norm.min():.4f}, {W_norm.max():.4f}]")
    print(f"  10. Retinotopy:               PENDING (not in MaleCNS v1.0)")
    print(f"  11. Validation assertions:    {passed}/{total} passed")
    print(f"  12. Final result:             {'PASS ✓' if passed == total else 'FAIL ✗'}")

    if passed != total:
        sys.exit(1)


if __name__ == "__main__":
    main()