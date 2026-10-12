"""Minimal required feature-only and linear temporal controls; train-only fit."""
import numpy as np
import yaml
from connectome.scripts.phase6.encoder import causal_hold
from .evidence import BASE


def load_config():
    config = yaml.safe_load((BASE / "completion_config.yaml").read_text())
    if config["version"] != "1.2.0" or config["spatial_seeds"] != [55010, 55011, 55012, 55013, 55014] or config["dt_ms"] != 1 or config["persistence_ms"] != 20 or config["input_scale"] != .4:
        raise ValueError("Unsupported completion condition")
    return config


def features_from_encoded(encoded, duration_ms=1000.0):
    if duration_ms != 1000.0:
        raise ValueError("Calibration benchmark requires 1 s clips")
    times = np.arange(1000, dtype=np.float64)
    drive = causal_hold(encoded.drive, encoded.timestamps_s, times / 1000)
    from connectome.scripts.phase6.encoder import load_mapping
    assigned = np.array(load_mapping()["channel_index"])
    # Every architecture receives the same full vector; primary broadcast makes these means lossless.
    if drive.shape != (1000, 321) or np.any(drive[:, assigned < 0] != 0):
        raise ValueError("Invalid full-vector control input")
    channels = np.column_stack([drive[:, assigned == k].mean(axis=1) for k in (0, 1)])
    for k in (0, 1):
        if not np.allclose(drive[:, assigned == k], channels[:, k:k+1], rtol=0, atol=1e-14):
            raise ValueError("Prerequisite controls require the primary uniform representation")
    filtered = np.zeros_like(channels)
    for k in range(999):
        filtered[k + 1] = filtered[k] + .1 * (-filtered[k] + .4 * channels[k])
    return times, .4 * channels.mean(axis=1), filtered


def fit_linear(training):
    if not training or any(r["split"] != "train" or r["cohort"] != "train" for r in training):
        raise ValueError("Linear fitting accepts training records only")
    if len({r["scenario_id"] for r in training}) != len(training):
        raise ValueError("Duplicate training scenario")
    x = np.array([r["filtered_features"][200:1000].max(axis=0) for r in training])
    y = np.array([r["label"] for r in training], dtype=np.float64)
    if x.shape != (len(training), 2) or not np.all(np.isfinite(x)) or np.any(x < 0) or not set(y).issubset({0., 1.}) or set(y) != {0., 1.}:
        raise ValueError("Invalid supervised linear training set")
    ridge = load_config()["linear_ridge"]
    choices = [np.zeros(2)]
    for active in ([0], [1], [0, 1]):
        xx = x[:, active]
        coefficient = np.linalg.solve(xx.T @ xx + ridge * np.eye(len(active)), xx.T @ y)
        if np.all(coefficient >= 0):
            weights = np.zeros(2)
            weights[active] = coefficient
            choices.append(weights)
    objective = lambda w: float(np.sum((x @ w - y) ** 2) + ridge * np.sum(w ** 2))
    weights = min(choices, key=objective)
    return dict(weights=weights.tolist(), bias=0.0, ridge=ridge, trainable_parameters=2,
                training_ids=[r["scenario_id"] for r in training], objective=objective(weights),
                fitting="exact two-variable nonnegative ridge active-set enumeration; train labels only")


def linear_score(filtered, model):
    weights = np.asarray(model["weights"], dtype=np.float64)
    if weights.shape != (2,) or not np.all(np.isfinite(weights)) or np.any(weights < 0) or model["bias"] != 0:
        raise ValueError("Invalid linear control")
    return filtered @ weights
