"""Verification suite for Phase 2 deliverables, checksums, and metrics."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
PHASE2_DIR = REPO_ROOT / "connectome" / "phase2"
RAW_DATA_DIR = REPO_ROOT / "connectome" / "data" / "raw"
PHASE3_DIR = REPO_ROOT / "connectome" / "phase3"

REQUIRED_DELIVERABLES = [
    "phase2_plan.md",
    "phase2_report.md",
    "candidate_dn_summary.csv",
    "candidate_dn_summary_w1.csv",
    "candidate_dn_summary_w3.csv",
    "candidate_dn_summary_w10.csv",
    "direct_visual_dn_edges.csv",
    "intermediate_candidates.csv",
    "two_step_paths.csv",
    "threshold_robustness.csv",
    "biological_evidence.md",
    "retinotopy_proxy.csv",
    "neurotransmitter_analysis.csv",
    "excluded_candidates.md",
    "circuit_v1_comparison.md",
    "phase2_decision_record.md",
    "phase2_provenance.json",
]

EXPECTED_CHECKSUMS = {
    "body-annotations-male-cns-v1.0-minconf-0.5.feather": "2177e246113e4cfbf1e7772ec37c6da1955ff22e8063d0b1f833101f99a9a3b2",
    "connectome-weights-male-cns-v1.0-minconf-0.5.feather": "e35da783d1c686b2b58b3b87cd6a403ae43bfcfba8bff28e08ef752c1a56afc1",
    "body-neurotransmitters-male-cns-v1.0.feather": "95c9289220663abeb3409f3ad9e5a7f8a53f8093f5139d15502cd08da8879621",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def check_deliverable_presence():
    print("Check 1: Verifying presence and non-emptiness of all 17 deliverables...")
    missing = []
    empty = []
    for name in REQUIRED_DELIVERABLES:
        p = PHASE2_DIR / name
        if not p.exists():
            missing.append(name)
        elif p.stat().st_size == 0:
            empty.append(name)

    assert not missing, f"Missing deliverables: {missing}"
    assert not empty, f"Empty deliverables: {empty}"
    print(f"  Passed: All {len(REQUIRED_DELIVERABLES)} deliverables exist and are non-empty.")


def check_source_checksums():
    print("Check 2: Verifying pinned source dataset checksums...")
    ann_path = RAW_DATA_DIR / "annotations" / "body-annotations-male-cns-v1.0-minconf-0.5.feather"
    conn_path = RAW_DATA_DIR / "connectivity" / "connectome-weights-male-cns-v1.0-minconf-0.5.feather"
    nt_path = RAW_DATA_DIR / "neurotransmitters" / "body-neurotransmitters-male-cns-v1.0.feather"

    assert sha256_file(ann_path) == EXPECTED_CHECKSUMS[ann_path.name]
    assert sha256_file(conn_path) == EXPECTED_CHECKSUMS[conn_path.name]
    assert sha256_file(nt_path) == EXPECTED_CHECKSUMS[nt_path.name]
    print("  Passed: Pinned raw datasets match expected SHA256 checksums.")


def check_candidate_dn_counts():
    print("Check 3: Verifying candidate descending neuron counts across thresholds...")
    df_w1 = pd.read_csv(PHASE2_DIR / "candidate_dn_summary_w1.csv")
    df_w3 = pd.read_csv(PHASE2_DIR / "candidate_dn_summary_w3.csv")
    df_w10 = pd.read_csv(PHASE2_DIR / "candidate_dn_summary_w10.csv")
    df_master = pd.read_csv(PHASE2_DIR / "candidate_dn_summary.csv")

    assert len(df_w1) == 63, f"Expected 63 candidates at w1, got {len(df_w1)}"
    assert len(df_w3) == 63, f"Expected 63 candidates in w3 table, got {len(df_w3)}"
    assert len(df_w10) == 63, f"Expected 63 candidates in w10 table, got {len(df_w10)}"
    assert len(df_master) == 63, f"Expected 63 candidates in master table, got {len(df_master)}"

    # Active candidates
    active_w1 = (df_w1["total_visual_weight"] > 0).sum()
    active_w3 = (df_w3["total_visual_weight"] > 0).sum()
    active_w10 = (df_w10["total_visual_weight"] > 0).sum()

    assert active_w1 == 63, f"Expected 63 active candidates at w1, got {active_w1}"
    assert active_w3 == 49, f"Expected 49 active candidates at w3, got {active_w3}"
    assert active_w10 == 33, f"Expected 33 active candidates at w10, got {active_w10}"

    print(f"  Passed: Active candidate counts verified (w1: {active_w1}, w3: {active_w3}, w10: {active_w10}).")


def check_direct_edges():
    print("Check 4: Verifying direct visual -> DN edges...")
    edges = pd.read_csv(PHASE2_DIR / "direct_visual_dn_edges.csv")
    assert len(edges) == 3611, f"Expected 3611 direct edges, got {len(edges)}"

    # Check for duplicate pairs
    dups = edges.duplicated(subset=["pre_bodyId", "post_bodyId"]).sum()
    assert dups == 0, f"Found {dups} duplicate edge pairs in direct_visual_dn_edges.csv"

    # Verify edge sums
    total_synapses = edges["weight"].sum()
    assert total_synapses == 57709, f"Expected 57,709 total visual synapses, got {total_synapses}"

    # Threshold counts
    surv_w3 = edges["survives_w3"].sum()
    surv_w10 = edges["survives_w10"].sum()
    assert surv_w3 == 2741, f"Expected 2741 edges surviving w3, got {surv_w3}"
    assert surv_w10 == 1590, f"Expected 1590 edges surviving w10, got {surv_w10}"

    print(f"  Passed: 3,611 edges verified without duplicates. Total synapses: {total_synapses:,}.")


def check_visual_share():
    print("Check 5: Verifying visual-input share bounds and values...")
    df = pd.read_csv(PHASE2_DIR / "candidate_dn_summary.csv")

    assert (df["visual_share_w1"] >= 0.0).all(), "Negative visual share found"
    assert (df["visual_share_w1"] <= 1.0).all(), "Visual share > 1.0 found"
    assert (df["visual_share_w3"] >= 0.0).all()
    assert (df["visual_share_w3"] <= 1.0).all()
    assert (df["visual_share_w10"] >= 0.0).all()
    assert (df["visual_share_w10"] <= 1.0).all()

    # Check reference DN values
    dnp04_rows = df[df["type"] == "DNp04"]
    assert len(dnp04_rows) == 2, "Expected 2 DNp04 neurons"
    for _, r in dnp04_rows.iterrows():
        assert 0.65 <= r["visual_share_w1"] <= 0.72, f"DNp04 visual share out of expected range: {r['visual_share_w1']}"

    dnp01_rows = df[df["type"] == "DNp01"]
    assert len(dnp01_rows) == 2, "Expected 2 DNp01 neurons"
    for _, r in dnp01_rows.iterrows():
        assert 0.24 <= r["visual_share_w1"] <= 0.28, f"DNp01 visual share out of expected range: {r['visual_share_w1']}"

    print("  Passed: Visual share bounds [0, 1] and reference candidate values verified.")


def check_retinotopy_and_neurotransmitters():
    print("Check 6: Verifying retinotopy proxy and neurotransmitter annotations...")
    ret_df = pd.read_csv(PHASE2_DIR / "retinotopy_proxy.csv")
    assert len(ret_df) == 374, f"Expected 374 neurons in retinotopy proxy, got {len(ret_df)}"
    assert not ret_df["retinotopic_column_available"].any(), "retinotopic_column_available must be False for all"

    nt_df = pd.read_csv(PHASE2_DIR / "neurotransmitter_analysis.csv")
    assert len(nt_df) == 424, f"Expected 424 neurons in neurotransmitter table, got {len(nt_df)}"
    assert not nt_df["functional_sign_justified"].any(), "functional_sign_justified must be False for all"

    print("  Passed: Retinotopy proxy and neurotransmitter analysis verified.")


def check_phase3_immutability():
    print("Check 7: Verifying immutability of Phase 3 artifacts...")
    # Check git status of connectome/phase3/
    result = subprocess.run(
        ["git", "status", "--porcelain", "connectome/phase3"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "", f"Phase 3 directory has uncommitted modifications:\n{result.stdout}"
    print("  Passed: Zero modifications to connectome/phase3/*.")


def check_provenance():
    print("Check 8: Verifying phase2_provenance.json...")
    prov_path = PHASE2_DIR / "phase2_provenance.json"
    with open(prov_path) as f:
        prov = json.load(f)

    assert prov["dataset"]["name"] == "MaleCNS v1.0"
    assert prov["thresholds_evaluated"] == [1, 3, 10]
    assert prov["parameters"]["direct_candidate_dn_count"] == 63
    print("  Passed: Provenance metadata verified.")


def main():
    print("=" * 60)
    print("FLY — Running Phase 2 Automated Verification Suite")
    print("=" * 60)

    try:
        check_deliverable_presence()
        check_source_checksums()
        check_candidate_dn_counts()
        check_direct_edges()
        check_visual_share()
        check_retinotopy_and_neurotransmitters()
        check_phase3_immutability()
        check_provenance()
        print("=" * 60)
        print("ALL 8 PHASE 2 VERIFICATION CHECKS PASSED.")
        print("=" * 60)
    except AssertionError as e:
        print(f"\nVERIFICATION FAILED: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
