"""Training-negative candidate construction; final calibration remains gated."""
import numpy as np
from .decoder import Threshold

POLICIES = {"raw_quantile_original_v1", "next_float_above_training_negative_quantile"}


def build_candidates(records, *, policy="next_float_above_training_negative_quantile", limit=32):
    if policy not in POLICIES or type(limit) is not int or limit != 32:
        raise ValueError("Unsupported threshold condition/search budget")
    if not records:
        raise ValueError("Training negative records required")
    ids = set()
    maxima = []
    for record in records:
        if record.get("split") != "train" or record.get("cohort") != "train" or record.get("label") != 0 or record.get("role") not in {"static_initial", "static_terminal", "translating_initial"}:
            raise ValueError("Candidate generation accepts training negatives only")
        if record.get("scenario_id") in ids or not isinstance(record.get("scenario_id"), str) or not isinstance(record.get("group_id"), str):
            raise ValueError("Training records must have unique scenario IDs and explicit family IDs")
        ids.add(record["scenario_id"])
        value = record.get("sustained_score_max")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not np.isfinite(value) or value < 0:
            raise ValueError("Training negative maxima must be finite and nonnegative")
        maxima.append(value)
    levels = np.linspace(0.0, 1.0, limit - 1)
    quantiles = np.quantile(np.array(maxima, dtype=np.float64), levels)
    by_value = {}
    for index, (level, raw) in enumerate(zip(levels, quantiles)):
        with np.errstate(over="ignore"):
            value = float(np.nextafter(raw, np.inf)) if policy != "raw_quantile_original_v1" else float(raw)
        if not np.isfinite(value):
            raise ValueError("Amended threshold overflow; do not replace with another condition")
        if value not in by_value:
            by_value[value] = dict(candidate_id=f"q{index:02d}", threshold=Threshold("finite", value).as_dict(), quantile_sources=[])
        by_value[value]["quantile_sources"].append(dict(index=index, level=float(level), raw_quantile=float(raw)))
    candidates = list(by_value.values())
    candidates.append(dict(candidate_id="always_silent", threshold=Threshold("always_silent", None).as_dict(), quantile_sources=[]))
    demo = next(c["candidate_id"] for c in candidates if any(q["level"] == 1.0 for q in c["quantile_sources"]))
    return dict(policy=policy, candidate_limit=limit, quantile_levels=levels.tolist(), training_negative_count=len(records),
                unique_finite_candidates=len(candidates) - 1, candidates=candidates,
                provisional_demo_candidate_id=demo, final_calibration_status="pending_required_controls_and_validation_selection")


def rank_validation_assessments(assessments):
    """Pure ranking rule for synthetic tests/future calibration; does not fit a model."""
    if not assessments:
        raise ValueError("Candidate assessments required")
    ids = set()
    valid = []
    for row in assessments:
        if row["candidate_id"] in ids:
            raise ValueError("Duplicate candidate assessment")
        ids.add(row["candidate_id"])
        threshold = Threshold(**row["threshold"])
        for key in ("timely_tpr", "full_episode_fpr"):
            if not np.isfinite(row[key]) or not 0 <= row[key] <= 1:
                raise ValueError("Invalid validation assessment")
        if row["full_episode_fpr"] <= 0.05:
            # Explicit sentinel ranks above any finite threshold if metrics tie.
            order = (row["timely_tpr"], -row["full_episode_fpr"], threshold.kind == "always_silent",
                     0.0 if threshold.value is None else threshold.value)
            valid.append((order, row))
    if not valid:
        raise ValueError("No feasible candidate; caller must include the silent sentinel")
    return max(valid, key=lambda pair: pair[0])[1]


def finalize_primary_calibration(*_args, **_kwargs):
    raise RuntimeError("Primary calibration is pending: feature-only and linear temporal controls must be integrated before final decoder tuning. Phase 8 provides candidates and a provisional demonstration only.")
