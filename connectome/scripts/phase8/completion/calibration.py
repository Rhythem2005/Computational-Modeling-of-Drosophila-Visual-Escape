"""Validation selection after actual prerequisite-control integration."""
import numpy as np
from connectome.scripts.phase8.decoder import Threshold, decode_score
from connectome.scripts.phase8.candidates import build_candidates, rank_validation_assessments
from .controls import load_config

MODELS = ("circuit", "feature_only", "linear_temporal")


def make_plan(training, model):
    if model not in MODELS:
        raise ValueError("Unknown model")
    records = []
    for r in training:
        if r["split"] != "train" or r["cohort"] != "train":
            raise ValueError("Candidate construction is training only")
        if r["label"] == 0:
            d = decode_score(r["times_ms"], r["scores"][model], 1000.0, Threshold("always_silent", None))
            records.append(dict(scenario_id=r["scenario_id"], group_id=r["group_id"], split="train", cohort="train", label=0,
                                role=r["role"], sustained_score_max=float(d.sustained_score[d.eligible].max())))
    return build_candidates(records)


def select_final(plan, validation, model, control_gate):
    if control_gate.get("status") != "PASS" or set(control_gate.get("integrated_models", [])) != {"feature_only", "linear_temporal"} or not control_gate.get("same_encoded_input_verified"):
        raise ValueError("Required feature-only and linear controls have not passed integration")
    if model not in MODELS or not validation or any(r["split"] != "validation" or r["cohort"] != "validation" for r in validation):
        raise ValueError("Selection accepts validation records only")
    if len({r["scenario_id"] for r in validation}) != len(validation):
        raise ValueError("Duplicate validation scenario")
    positives = sum(r["label"] == 1 for r in validation)
    negatives = sum(r["label"] == 0 for r in validation)
    if positives == 0 or negatives == 0 or positives + negatives != len(validation):
        raise ValueError("Both binary validation classes are required")
    assessments = []
    predictions = []
    for candidate in plan["candidates"]:
        threshold = Threshold(**candidate["threshold"])
        timely = false_positive = early = 0
        details = []
        for r in validation:
            decoded = decode_score(r["times_ms"], r["scores"][model], 1000.0, threshold)
            first = decoded.first_event_ms
            in_window = first is not None and 200 <= first < 1000
            timely += r["label"] == 1 and in_window
            false_positive += r["label"] == 0 and first is not None
            early += first is not None and first < 200
            details.append(dict(scenario_id=r["scenario_id"], first_event_ms=first, label=r["label"], timely=in_window))
        assessments.append(dict(candidate_id=candidate["candidate_id"], threshold=threshold.as_dict(),
                                timely_tpr=timely / positives, full_episode_fpr=false_positive / negatives,
                                pre_onset_decisions=early, validation_positives=positives, validation_negatives=negatives))
        predictions.append(dict(candidate_id=candidate["candidate_id"], predictions=details))
    selected = rank_validation_assessments(assessments)
    return dict(model=model, status="validation_selected", threshold=selected["threshold"], selected_candidate_id=selected["candidate_id"],
                assessments=assessments, candidate_predictions=predictions, selected_assessment=selected,
                validation_ids=[r["scenario_id"] for r in validation], rule="max timely TPR with negative full-episode FPR<=0.05; tie lower FPR then higher threshold")
