"""Proof-checked final initiation and explicit neutral/synthetic steering commands."""
from pathlib import Path
import json
import numpy as np
from connectome.scripts.phase8.decoder import InitiationDecoder, Threshold
from connectome.scripts.phase6.encoder import digest, load_mapping
from .evidence import ROOT, BASE, OUT, file_hash, verify_checkpoint
from .controls import load_config


def load_freeze(path=OUT / "calibration_freeze.json"):
    verify_checkpoint()
    path = Path(path)
    freeze = json.loads(path.read_text())
    payload = dict(freeze)
    expected_hash = payload.pop("payload_sha256", None)
    if expected_hash != digest(payload) or freeze.get("status") != "calibrated_frozen":
        raise ValueError("Invalid calibration freeze")
    if freeze["completion_config_sha256"] != digest(load_config()):
        raise ValueError("Completion config changed after calibration")
    for name, expected in freeze["sources_sha256"].items():
        if file_hash(ROOT / name) != expected:
            raise ValueError(f"Completion source changed after calibration: {name}")
    for name, expected in freeze["prerequisite_artifacts_sha256"].items():
        if file_hash(ROOT / name) != expected:
            raise ValueError(f"Calibration prerequisite changed: {name}")
    if set(freeze["models"]) != {"circuit", "feature_only", "linear_temporal"} or freeze["control_gate"]["status"] != "PASS":
        raise ValueError("Missing calibrated prerequisites")
    return freeze


def steering_commands(decoded, *, condition, gains=(1.0, 1.0)):
    if condition not in {"uniform_population", "synthetic_fields_within_type_and_side_v1"}:
        raise ValueError("Unsupported steering representation; no inferred anatomy")
    turn = np.zeros(len(decoded.times_ms), dtype=np.float64)
    raw = np.zeros_like(turn)
    if condition == "synthetic_fields_within_type_and_side_v1":
        indices = {int(bid): k for k, bid in enumerate(decoded.dn_body_ids)}
        if 10228 not in indices or 10584 not in indices:
            raise ValueError("Missing bilateral DNp06 steering source")
        gains = np.asarray(gains, dtype=np.float64)
        if gains.shape != (2,) or not np.all(np.isfinite(gains)) or np.any(gains <= 0):
            raise ValueError("Steering gains must be positive finite training-only normalizers")
        left = decoded.dn_activity[:, indices[10228]] / gains[0]
        right = decoded.dn_activity[:, indices[10584]] / gains[1]
        total = left + right
        np.divide(left - right, total, out=raw, where=total > 0)
        if decoded.first_event_ms is not None:
            k = int(decoded.first_event_ms)
            turn[k:] = raw[k]
    return dict(turn_command=turn, raw_dn_imbalance=raw,
                mode="unsteered_primary" if condition == "uniform_population" else "synthetic_engineered_turn",
                condition_id=condition, positive_turn="rightward", units="normalized request [-1,1]",
                biological_mapping_validated=False)


class CalibratedDecoder:
    def __init__(self, freeze_path=OUT / "calibration_freeze.json"):
        self.freeze = load_freeze(freeze_path)
        self.core = InitiationDecoder(Threshold(**self.freeze["models"]["circuit"]["threshold"]))

    def decode_activity(self, times_ms, states, body_ids, duration_ms, *, condition="uniform_population", spatial_mapping=None):
        mapping_hash = None
        if condition != "uniform_population":
            from .spatial import assign_fields
            if not isinstance(spatial_mapping, dict) or "seed" not in spatial_mapping:
                raise ValueError("Synthetic steering requires its independently documented mapping")
            expected = assign_fields(load_mapping()["nodes"], spatial_mapping["seed"])
            if digest(expected) != digest(spatial_mapping):
                raise ValueError("Spatial mapping differs from the predeclared condition")
            mapping_hash = digest(spatial_mapping)
        decoded = self.core.decode_activity(times_ms, states, body_ids, duration_ms)
        decoded.threshold_status = "validation_selected_frozen"
        steering = steering_commands(decoded, condition=condition, gains=self.freeze["steering_normalization"]["gains"])
        action = decoded.action()
        value = 0.0 if decoded.first_event_ms is None else float(steering["turn_command"][int(decoded.first_event_ms)])
        action.update(steering=value, steering_status=steering["mode"], condition_id=condition,
                      calibration_sha256=self.freeze["payload_sha256"],
                      initiation_calibration_scope="uniform_population" if condition == "uniform_population" else "uniform threshold reused for integration fixture; spatial condition not separately calibrated",
                      motor_mapping="neutral for primary; DNp06 normalized imbalance for synthetic condition",
                      biological_mapping_validated=False, spatial_mapping_sha256=mapping_hash)
        if condition != "uniform_population":
            action["threshold_status"] = "primary_frozen_threshold_reused_uncalibrated_spatial_fixture"
        return decoded, steering, action
