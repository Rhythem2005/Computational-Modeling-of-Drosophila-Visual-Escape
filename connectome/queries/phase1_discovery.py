"""
phase1_discovery.py — Phase 1: Full-Connectome Circuit Discovery

Queries the local MaleCNS v1.0 dataset (feather files) to identify:
  1. LC4 and LPLC2 populations
  2. DNp01, DNp04, DNp06 populations
  3. The complete descending-neuron population
  4. All major downstream targets of LC4 and LPLC2
  5. Convergence neurons receiving both LC4 and LPLC2 input
  6. Descending neurons receiving direct visual input
  7. Quantitative comparison of named DN candidates
  8. Upstream structure of candidate DNs
  9. Two-step pathways: visual → intermediate → DN
 10. Direct versus indirect comparison
 11. Evidence summary

Descending neurons are identified via:
    superclass == 'descending_neuron'
in the MaleCNS v1.0 body-annotations file.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.ipc as ipc


VISUAL_TYPES = ["LC4", "LPLC2"]
NAMED_DNS = ["DNp01", "DNp04", "DNp06"]


def normalize_text(series: pd.Series) -> pd.Series:
    return (
        series.astype("string")
        .str.strip()
        .str.lower()
    )


def stream_feather_batches(path: Path):
    """
    Stream an Arrow/Feather IPC file without loading the entire file.
    """
    source = pa.memory_map(str(path), "r")

    try:
        reader = ipc.open_file(source)

        for i in range(reader.num_record_batches):
            yield reader.get_batch(i)

    finally:
        source.close()


def scan_edges(
    connectivity_path: Path,
    *,
    pre_ids: set[int] | None = None,
    post_ids: set[int] | None = None,
) -> pd.DataFrame:
    """
    Stream the connectivity file and return only matching edges.

    When both pre_ids and post_ids are given, returns edges
    where pre is in pre_ids OR post is in post_ids (union),
    unless caller needs intersection (handled externally).
    """
    if pre_ids is None and post_ids is None:
        raise ValueError("At least one of pre_ids/post_ids is required.")

    pre_values = (
        pa.array(sorted(pre_ids), type=pa.int64())
        if pre_ids
        else None
    )

    post_values = (
        pa.array(sorted(post_ids), type=pa.int64())
        if post_ids
        else None
    )

    chunks: list[pd.DataFrame] = []

    for batch in stream_feather_batches(connectivity_path):
        table = batch.select(["body_pre", "body_post", "weight"])

        mask = None

        if pre_values is not None:
            pre = pc.cast(table["body_pre"], pa.int64(), safe=False)
            current = pc.is_in(pre, value_set=pre_values)
            mask = np.asarray(current)

        if post_values is not None:
            post = pc.cast(table["body_post"], pa.int64(), safe=False)
            current = np.asarray(
                pc.is_in(post, value_set=post_values)
            )

            if mask is None:
                mask = current
            elif pre_ids is not None and post_ids is not None:
                # When both are given, use AND (intersection)
                mask = mask & current
            else:
                mask = current

        if mask is None or not mask.any():
            continue

        filtered = table.filter(pa.array(mask))
        chunks.append(filtered.to_pandas())

    if not chunks:
        return pd.DataFrame(
            columns=["body_pre", "body_post", "weight"]
        )

    edges = pd.concat(chunks, ignore_index=True)

    edges["body_pre"] = pd.to_numeric(
        edges["body_pre"], errors="raise"
    ).astype(np.int64)

    edges["body_post"] = pd.to_numeric(
        edges["body_post"], errors="raise"
    ).astype(np.int64)

    edges["weight"] = pd.to_numeric(
        edges["weight"], errors="raise"
    )

    return edges


def aggregate_edges(edges: pd.DataFrame) -> pd.DataFrame:
    if edges.empty:
        return edges.copy()

    return (
        edges
        .groupby(
            ["body_pre", "body_post"],
            as_index=False,
            sort=False,
        )["weight"]
        .sum()
    )


def load_annotations(annotation_path: Path):
    """
    Load annotation metadata needed for circuit discovery.

    Descending neurons are identified via:
        superclass == 'descending_neuron'
    (NOT by looking for the literal string 'descending_neuron' in the type column.)
    """
    ann = pd.read_feather(
        annotation_path,
        columns=[
            "bodyId",
            "type",
            "superclass",
        ],
    )

    ann["bodyId"] = pd.to_numeric(
        ann["bodyId"],
        errors="coerce",
    ).astype("Int64")

    ann = ann.dropna(subset=["bodyId"]).copy()
    ann["bodyId"] = ann["bodyId"].astype(np.int64)

    ann["type_norm"] = normalize_text(ann["type"])
    ann["superclass_norm"] = normalize_text(ann["superclass"])

    # Build type map: bodyId -> type string
    type_map = (
        ann.groupby("bodyId")["type"]
        .agg(
            lambda values: "|".join(
                sorted(
                    {
                        str(v).strip()
                        for v in values
                        if pd.notna(v) and str(v).strip()
                    }
                )
            )
        )
        .to_dict()
    )

    # Identify named populations by type
    populations: dict[str, set[int]] = {}

    for cell_type in VISUAL_TYPES + NAMED_DNS:
        ids = set(
            ann.loc[
                ann["type_norm"] == cell_type.lower(),
                "bodyId",
            ].tolist()
        )

        populations[cell_type] = ids

    # Identify descending neurons by superclass
    descending_mask = ann["superclass_norm"] == "descending_neuron"
    descending_ids = set(
        ann.loc[descending_mask, "bodyId"].tolist()
    )

    # Also note related categories (not included in primary set)
    related_descending = {}
    for label in [
        "descending_neuron_tbc",
        "sensory_descending",
        "efferent_descending",
    ]:
        related_mask = ann["superclass_norm"] == label
        related_ids = set(
            ann.loc[related_mask, "bodyId"].tolist()
        )
        if related_ids:
            related_descending[label] = related_ids

    if not descending_ids:
        raise RuntimeError(
            "No neurons with superclass == 'descending_neuron' found "
            "in the annotation file. Check the data."
        )

    return (
        ann,
        type_map,
        populations,
        descending_ids,
        related_descending,
    )


def add_target_type(edges: pd.DataFrame, type_map: dict[int, str]):
    result = edges.copy()

    result["source_type"] = result["body_pre"].map(
        type_map
    ).fillna("UNKNOWN")

    result["target_type"] = result["body_post"].map(
        type_map
    ).fillna("UNKNOWN")

    return result


def save_csv(df: pd.DataFrame, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def population_inventory(
    populations: dict[str, set[int]],
    output_dir: Path,
):
    rows = []

    for cell_type, ids in populations.items():
        for body_id in sorted(ids):
            rows.append(
                {
                    "population": cell_type,
                    "bodyId": body_id,
                }
            )

    save_csv(
        pd.DataFrame(rows),
        output_dir / "population_inventory.csv",
    )


def direct_visual_outputs(
    connectivity_path: Path,
    type_map: dict[int, str],
    populations: dict[str, set[int]],
    output_dir: Path,
):
    all_visual_edges = []

    for visual_type in VISUAL_TYPES:
        ids = populations[visual_type]

        print(
            f"  Extracting {visual_type} outputs "
            f"from {len(ids):,} neurons..."
        )

        edges = scan_edges(
            connectivity_path,
            pre_ids=ids,
        )

        edges = aggregate_edges(edges)

        edges["source_type"] = visual_type

        save_csv(
            add_target_type(edges, type_map),
            output_dir / f"{visual_type.lower()}_outputs.csv",
        )

        all_visual_edges.append(edges)

    if not all_visual_edges:
        return pd.DataFrame()

    return pd.concat(
        all_visual_edges,
        ignore_index=True,
    )


def common_targets(
    visual_edges: pd.DataFrame,
    type_map: dict[int, str],
    output_dir: Path,
):
    target_summary = (
        visual_edges
        .groupby(
            ["source_type", "body_post"],
            as_index=False,
        )["weight"]
        .sum()
    )

    pivot = (
        target_summary
        .pivot(
            index="body_post",
            columns="source_type",
            values="weight",
        )
        .fillna(0.0)
        .reset_index()
    )

    for column in VISUAL_TYPES:
        if column not in pivot.columns:
            pivot[column] = 0.0

    pivot["target_type"] = (
        pivot["body_post"]
        .map(type_map)
        .fillna("UNKNOWN")
    )

    pivot["receives_from_both"] = (
        (pivot["LC4"] > 0)
        & (pivot["LPLC2"] > 0)
    )

    pivot = pivot.sort_values(
        ["receives_from_both", "LC4", "LPLC2"],
        ascending=[False, False, False],
    )

    save_csv(
        pivot,
        output_dir / "common_visual_targets.csv",
    )

    by_type = (
        target_summary
        .assign(
            target_type=lambda df:
                df["body_post"].map(type_map).fillna("UNKNOWN")
        )
        .groupby(
            ["source_type", "target_type"],
            as_index=False,
        )
        .agg(
            target_neurons=("body_post", "nunique"),
            total_weight=("weight", "sum"),
        )
        .sort_values(
            ["source_type", "total_weight"],
            ascending=[True, False],
        )
    )

    save_csv(
        by_type,
        output_dir / "visual_downstream_by_type.csv",
    )

    return pivot


def descending_targets(
    visual_edges: pd.DataFrame,
    descending_ids: set[int],
    type_map: dict[int, str],
    output_dir: Path,
):
    direct = visual_edges[
        visual_edges["body_post"].isin(descending_ids)
    ].copy()

    direct["descending_type"] = (
        direct["body_post"]
        .map(type_map)
        .fillna("UNKNOWN")
    )

    save_csv(
        direct.sort_values(
            ["descending_type", "weight"],
            ascending=[True, False],
        ),
        output_dir / "visual_descending_edges.csv",
    )

    ranked = (
        direct
        .groupby(
            ["body_post", "descending_type", "source_type"],
            as_index=False,
        )["weight"]
        .sum()
        .pivot(
            index=["body_post", "descending_type"],
            columns="source_type",
            values="weight",
        )
        .fillna(0.0)
        .reset_index()
    )

    for column in VISUAL_TYPES:
        if column not in ranked.columns:
            ranked[column] = 0.0

    ranked["total_visual_weight"] = (
        ranked["LC4"] + ranked["LPLC2"]
    )

    ranked["receives_both"] = (
        (ranked["LC4"] > 0) & (ranked["LPLC2"] > 0)
    )

    ranked = ranked.sort_values(
        "total_visual_weight",
        ascending=False,
    )

    save_csv(
        ranked,
        output_dir / "visual_descending_targets.csv",
    )

    return ranked


def named_dn_comparison(
    visual_edges: pd.DataFrame,
    populations: dict[str, set[int]],
    output_dir: Path,
):
    rows = []

    for dn_type in NAMED_DNS:
        dn_ids = populations[dn_type]

        subset = visual_edges[
            visual_edges["body_post"].isin(dn_ids)
        ]

        for visual_type in VISUAL_TYPES:
            weight = subset.loc[
                subset["source_type"] == visual_type,
                "weight",
            ].sum()

            rows.append(
                {
                    "descending_type": dn_type,
                    "neuron_count": len(dn_ids),
                    "visual_source": visual_type,
                    "total_input_weight": float(weight),
                }
            )

    result = pd.DataFrame(rows)

    wide = (
        result
        .pivot(
            index=[
                "descending_type",
                "neuron_count",
            ],
            columns="visual_source",
            values="total_input_weight",
        )
        .fillna(0.0)
        .reset_index()
    )

    for column in VISUAL_TYPES:
        if column not in wide.columns:
            wide[column] = 0.0

    wide["total_visual_input"] = (
        wide["LC4"] + wide["LPLC2"]
    )

    wide = wide.sort_values(
        "total_visual_input",
        ascending=False,
    )

    save_csv(
        wide,
        output_dir / "named_descending_comparison.csv",
    )

    return wide


def upstream_analysis(
    connectivity_path: Path,
    type_map: dict[int, str],
    populations: dict[str, set[int]],
    descending_ranked: pd.DataFrame,
    output_dir: Path,
    top_k: int,
):
    """
    Analyze all incoming connectivity for DNp01/DNp04/DNp06
    plus the top-K additional direct descending candidates.
    """
    named_ids = set().union(
        *(populations[name] for name in NAMED_DNS)
    )

    additional_ids = set(
        descending_ranked[
            ~descending_ranked["body_post"].isin(named_ids)
        ]
        .head(top_k)["body_post"]
        .tolist()
    )

    candidate_ids = named_ids | additional_ids

    print(
        f"  Extracting upstream connectivity for "
        f"{len(candidate_ids):,} descending neurons..."
    )

    incoming = scan_edges(
        connectivity_path,
        post_ids=candidate_ids,
    )

    incoming = aggregate_edges(incoming)

    incoming["source_type"] = (
        incoming["body_pre"]
        .map(type_map)
        .fillna("UNKNOWN")
    )

    incoming["descending_type"] = (
        incoming["body_post"]
        .map(type_map)
        .fillna("UNKNOWN")
    )

    save_csv(
        incoming,
        output_dir / "candidate_descending_inputs.csv",
    )

    for dn_type in NAMED_DNS:
        dn_ids = populations[dn_type]

        subset = incoming[
            incoming["body_post"].isin(dn_ids)
        ].copy()

        profile = (
            subset
            .groupby(
                ["body_post", "source_type"],
                as_index=False,
            )["weight"]
            .sum()
            .sort_values(
                "weight",
                ascending=False,
            )
        )

        save_csv(
            profile,
            output_dir / f"{dn_type.lower()}_inputs.csv",
        )

    return incoming


def two_step_paths(
    connectivity_path: Path,
    visual_edges: pd.DataFrame,
    descending_ids: set[int],
    type_map: dict[int, str],
    visual_ids: set[int],
    output_dir: Path,
):
    """
    Search:
        LC4/LPLC2 -> intermediate -> descending neuron
    """

    intermediate_ids = set(
        visual_edges["body_post"].unique()
    )

    intermediate_ids -= descending_ids
    intermediate_ids -= visual_ids

    print(
        f"  Searching second-order paths through "
        f"{len(intermediate_ids):,} candidate intermediates..."
    )

    second_edges = scan_edges(
        connectivity_path,
        pre_ids=intermediate_ids,
        post_ids=descending_ids,
    )

    second_edges = aggregate_edges(second_edges)

    if second_edges.empty:
        save_csv(
            pd.DataFrame(),
            output_dir / "two_step_visual_descending_paths.csv",
        )
        save_csv(
            pd.DataFrame(),
            output_dir / "two_step_visual_descending_by_type.csv",
        )
        return pd.DataFrame()

    visual_to_intermediate = (
        visual_edges[
            visual_edges["body_post"].isin(intermediate_ids)
        ]
        .groupby(
            ["source_type", "body_post"],
            as_index=False,
        )["weight"]
        .sum()
        .rename(
            columns={
                "body_post": "intermediate_body",
                "weight": "visual_to_intermediate_weight",
            }
        )
    )

    intermediate_to_dn = (
        second_edges
        .rename(
            columns={
                "body_pre": "intermediate_body",
                "body_post": "descending_body",
                "weight": "intermediate_to_descending_weight",
            }
        )
    )

    paths = visual_to_intermediate.merge(
        intermediate_to_dn,
        on="intermediate_body",
        how="inner",
    )

    paths["intermediate_type"] = (
        paths["intermediate_body"]
        .map(type_map)
        .fillna("UNKNOWN")
    )

    paths["descending_type"] = (
        paths["descending_body"]
        .map(type_map)
        .fillna("UNKNOWN")
    )

    paths = paths.sort_values(
        [
            "descending_type",
            "visual_to_intermediate_weight",
            "intermediate_to_descending_weight",
        ],
        ascending=[True, False, False],
    )

    save_csv(
        paths,
        output_dir / "two_step_visual_descending_paths.csv",
    )

    by_type = (
        paths
        .groupby(
            [
                "source_type",
                "intermediate_type",
                "descending_type",
            ],
            as_index=False,
        )
        .agg(
            intermediate_neurons=(
                "intermediate_body",
                "nunique",
            ),
            path_instances=(
                "intermediate_body",
                "size",
            ),
            total_visual_to_intermediate_weight=(
                "visual_to_intermediate_weight",
                "sum",
            ),
            total_intermediate_to_descending_weight=(
                "intermediate_to_descending_weight",
                "sum",
            ),
        )
        .sort_values(
            "total_intermediate_to_descending_weight",
            ascending=False,
        )
    )

    save_csv(
        by_type,
        output_dir / "two_step_visual_descending_by_type.csv",
    )

    return paths


def direct_vs_indirect_comparison(
    descending_ranked: pd.DataFrame,
    two_step_df: pd.DataFrame,
    type_map: dict[int, str],
    output_dir: Path,
):
    """
    Compare direct (visual → DN) versus indirect (visual → intermediate → DN)
    input for each descending candidate.
    """
    # Direct input summary
    direct = (
        descending_ranked[["body_post", "descending_type", "total_visual_weight"]]
        .rename(columns={
            "body_post": "descending_body",
            "total_visual_weight": "direct_visual_weight",
        })
    )

    if two_step_df.empty:
        direct["indirect_visual_weight"] = 0.0
        direct["total_weight"] = direct["direct_visual_weight"]
        direct["direct_fraction"] = 1.0
        save_csv(
            direct.sort_values("total_weight", ascending=False),
            output_dir / "direct_vs_indirect_comparison.csv",
        )
        return direct

    # Indirect input summary: sum all intermediate→DN weights per DN
    indirect = (
        two_step_df
        .groupby(
            ["descending_body", "descending_type"],
            as_index=False,
        )
        .agg(
            indirect_visual_weight=(
                "intermediate_to_descending_weight",
                "sum",
            ),
            indirect_pathway_count=(
                "intermediate_body",
                "nunique",
            ),
        )
    )

    comparison = direct.merge(
        indirect,
        on=["descending_body", "descending_type"],
        how="outer",
    ).fillna(0.0)

    comparison["total_weight"] = (
        comparison["direct_visual_weight"]
        + comparison["indirect_visual_weight"]
    )

    comparison["direct_fraction"] = np.where(
        comparison["total_weight"] > 0,
        comparison["direct_visual_weight"] / comparison["total_weight"],
        0.0,
    )

    comparison = comparison.sort_values(
        "total_weight",
        ascending=False,
    )

    save_csv(
        comparison,
        output_dir / "direct_vs_indirect_comparison.csv",
    )

    return comparison


def write_research_queue(
    descending_ranked: pd.DataFrame,
    common_df: pd.DataFrame,
    output_dir: Path,
):
    lines = [
        "# Phase 1 — Literature Review Queue",
        "",
        "Use this file as a research checklist after computational discovery.",
        "",
        "## Candidate descending populations",
        "",
    ]

    candidate_types = (
        descending_ranked["descending_type"]
        .drop_duplicates()
        .head(30)
        .tolist()
    )

    for candidate in candidate_types:
        lines.append(f"- {candidate}")

    lines.extend(
        [
            "",
            "## Candidate shared visual targets",
            "",
        ]
    )

    shared = common_df[
        common_df["receives_from_both"]
    ]

    for target in (
        shared["target_type"]
        .drop_duplicates()
        .head(30)
        .tolist()
    ):
        lines.append(f"- {target}")

    lines.extend(
        [
            "",
            "Review official 2026 MaleCNS documentation and relevant "
            "2026 biological/connectome literature for these candidates.",
        ]
    )

    (output_dir / "research_queue.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--root",
        type=Path,
        default=Path("data/male_cns_v1"),
    )

    parser.add_argument(
        "--top-k-upstream",
        type=int,
        default=25,
    )

    args = parser.parse_args()

    connectivity_path = (
        args.root
        / "connectivity"
        / "connectome-weights-male-cns-v1.0-minconf-0.5.feather"
    )

    annotation_path = (
        args.root
        / "annotations"
        / "body-annotations-male-cns-v1.0-minconf-0.5.feather"
    )

    output_dir = args.root / "discovery"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not connectivity_path.exists():
        raise FileNotFoundError(connectivity_path)

    if not annotation_path.exists():
        raise FileNotFoundError(annotation_path)

    # ── Load annotations ─────────────────────────────────────────
    print("Loading annotations...")

    (
        annotation,
        type_map,
        populations,
        descending_ids,
        related_descending,
    ) = load_annotations(annotation_path)

    print("\nPopulation counts:")

    for name, ids in populations.items():
        print(f"  {name:8s}: {len(ids):,}")

    print(
        f"  descending: {len(descending_ids):,}"
        f"  (superclass == 'descending_neuron')"
    )

    for label, ids in related_descending.items():
        print(f"  {label}: {len(ids):,}")

    # ── Step 1: Population inventory ─────────────────────────────
    print("\n[Step 1] Saving population inventory...")
    population_inventory(
        populations,
        output_dir,
    )

    save_csv(
        pd.DataFrame(
            {
                "bodyId": sorted(descending_ids),
                "type": [
                    type_map.get(body_id, "UNKNOWN")
                    for body_id in sorted(descending_ids)
                ],
            }
        ),
        output_dir / "descending_neurons.csv",
    )

    # ── Steps 2-3: Direct visual outputs ─────────────────────────
    print("\n[Steps 2-3] Extracting direct visual outputs...")
    visual_edges = direct_visual_outputs(
        connectivity_path,
        type_map,
        populations,
        output_dir,
    )

    # ── Step 4: Common targets ───────────────────────────────────
    print("\n[Step 4] Analyzing common visual targets...")
    common = common_targets(
        visual_edges,
        type_map,
        output_dir,
    )

    # ── Steps 5+7: Descending targets ────────────────────────────
    print("\n[Steps 5+7] Identifying descending targets...")
    descending_ranked = descending_targets(
        visual_edges,
        descending_ids,
        type_map,
        output_dir,
    )

    # ── Step 6: Named DN comparison ──────────────────────────────
    print("\n[Step 6] Comparing DNp01/DNp04/DNp06...")
    named = named_dn_comparison(
        visual_edges,
        populations,
        output_dir,
    )

    # ── Step 8: Upstream analysis ────────────────────────────────
    print("\n[Step 8] Analyzing upstream structure...")
    upstream_analysis(
        connectivity_path,
        type_map,
        populations,
        descending_ranked,
        output_dir,
        args.top_k_upstream,
    )

    # ── Steps 9-10: Two-step paths ───────────────────────────────
    print("\n[Steps 9-10] Searching two-step pathways...")
    visual_ids = set().union(
        *(populations[name] for name in VISUAL_TYPES)
    )

    two_step_df = two_step_paths(
        connectivity_path,
        visual_edges,
        descending_ids,
        type_map,
        visual_ids,
        output_dir,
    )

    # ── Step 11: Direct vs indirect comparison ───────────────────
    print("\n[Step 11] Comparing direct vs indirect pathways...")
    direct_vs_indirect_comparison(
        descending_ranked,
        two_step_df,
        type_map,
        output_dir,
    )

    # ── Step 12: Research queue ──────────────────────────────────
    print("\n[Step 12] Writing research queue...")
    write_research_queue(
        descending_ranked,
        common,
        output_dir,
    )

    # ── Step 13: Summary ─────────────────────────────────────────
    print("\n[Step 13] Writing discovery summary...")

    # Top descending candidates
    top_descending = (
        descending_ranked.head(20).to_dict(orient="records")
    )

    # Convergence stats
    both_count = int(common["receives_from_both"].sum())
    convergence_types = (
        common[common["receives_from_both"]]
        ["target_type"]
        .value_counts()
        .head(20)
        .to_dict()
    )

    summary = {
        "dataset": "MaleCNS v1.0",
        "identification_method": {
            "descending_neurons": "superclass == 'descending_neuron'",
            "visual_types": "type column exact match",
            "named_dns": "type column exact match",
        },
        "visual_types": VISUAL_TYPES,
        "named_descending_types": NAMED_DNS,
        "population_counts": {
            name: len(ids)
            for name, ids in populations.items()
        },
        "descending_neuron_count": len(descending_ids),
        "related_descending": {
            label: len(ids)
            for label, ids in related_descending.items()
        },
        "visual_edge_rows_after_aggregation": len(
            visual_edges
        ),
        "shared_target_count": both_count,
        "shared_target_type_distribution": convergence_types,
        "direct_descending_candidate_count": len(
            descending_ranked
        ),
        "descending_receiving_both_visual": int(
            descending_ranked["receives_both"].sum()
        ) if "receives_both" in descending_ranked.columns else 0,
        "named_descending_comparison": (
            named.to_dict(orient="records")
        ),
        "top_descending_candidates": top_descending,
        "two_step_path_count": len(two_step_df),
    }

    (output_dir / "discovery_summary.json").write_text(
        json.dumps(
            summary,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    print("\n" + "=" * 60)
    print("Phase 1 discovery complete.")
    print(f"Results: {output_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()