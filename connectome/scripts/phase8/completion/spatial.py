"""Explicit synthetic fields independent of connectivity and outcomes."""
from copy import deepcopy
import numpy as np
from connectome.scripts.phase6.encoder import load_mapping, digest, CausalEncoder
from connectome.scripts.phase4 import simulator
from .controls import load_config


def assign_fields(nodes, seed):
    config = load_config()
    if seed not in config["spatial_seeds"]:
        raise ValueError("Use all five predeclared mapping seeds; no new seed search")
    rng = np.random.default_rng(seed)
    fields = []
    for ntype in ("LC4", "LPLC2"):
        for side in ("left", "right"):
            members = sorted((n for n in nodes if n["type"] == ntype and n["side"] == side), key=lambda n: n["bodyId"])
            low, high = (-1.0, 0.0) if side == "left" else (0.0, 1.0)
            for node in members:
                fields.append(dict(bodyId=int(node["bodyId"]), type=ntype, side=side,
                                   center_x=float(rng.uniform(low, high)), center_y=float(rng.uniform(-1, 1))))
    if len(fields) != 311 or len({f["bodyId"] for f in fields}) != 311:
        raise ValueError("Synthetic fields require all 311 frozen visual neurons")
    return dict(version="1.0", condition_id=config["spatial_condition"], seed=seed,
                sigma=config["field_sigma_normalized"], fields=fields,
                convention="normalized image +x right, +y up; left cells assigned left half by assumption",
                assignment_inputs=["visual neuron identity", "type", "side", "seed"],
                biological_retinotopy=False, fit_trials=0)


def frame_drive(encoder, frames, timestamps_s, mapping):
    expected = assign_fields(encoder.mapping["nodes"], mapping["seed"])
    if digest(mapping) != digest(expected):
        raise ValueError("Synthetic field assignment differs from the predeclared seed")
    global_encoded = encoder.encode(frames, timestamps_s)
    if frames.shape[1] < 2 or frames.shape[2] < 2:
        raise ValueError("Spatial normalization requires image width/height >=2")
    ids = {bid: k for k, bid in enumerate(global_encoded.body_ids)}
    drive = np.zeros_like(global_encoded.drive)
    centroids = np.zeros((len(frames), 2), dtype=np.float64)
    valid = global_encoded.diagnostics["valid"]
    width, height = frames.shape[2], frames.shape[1]
    centers = np.array([[f["center_x"], f["center_y"]] for f in mapping["fields"]])
    columns = np.array([ids[f["bodyId"]] for f in mapping["fields"]])
    for k, frame in enumerate(frames):
        if not valid[k]:
            continue
        background = int(np.argmax(np.bincount(frame.ravel(), minlength=256)))
        mask = np.abs(frame.astype(np.int16) - background) >= encoder.config["min_contrast_uint8"]
        yy, xx = np.nonzero(mask)
        centroids[k] = [2 * xx.mean() / (width - 1) - 1, 1 - 2 * yy.mean() / (height - 1)]
        squared = np.sum((centers - centroids[k]) ** 2, axis=1)
        weights = np.exp(-squared / (2 * mapping["sigma"] ** 2))
        drive[k, columns] = global_encoded.drive[k, columns] * weights
    if not np.all(np.isfinite(drive)) or np.any(drive < 0) or np.any(drive > 1):
        raise RuntimeError("Invalid spatial drive")
    return global_encoded, drive, centroids


def simulate_spatial(pipeline, frames, timestamps_s, duration_ms, mapping):
    encoded, drive, centroids = frame_drive(pipeline.encoder, frames, timestamps_s, mapping)
    if timestamps_s[-1] >= duration_ms / 1000:
        raise ValueError("Frame timestamp outside spatial episode")
    config = deepcopy(pipeline.simulation_config)
    config["duration"] = duration_ms
    def callback(t_ms, n):
        if n != len(encoded.body_ids):
            raise ValueError("Spatial input dimension mismatch")
        index = np.searchsorted(timestamps_s, t_ms / 1000, side="right") - 1
        return np.zeros(n) if index < 0 else drive[index].copy()
    times, states, _ = simulator.run_simulation(pipeline.circuit, config, callback)
    if not np.all(np.isfinite(states)) or np.any(states < 0):
        raise RuntimeError("Nonfinite/negative spatial simulation; do not replace seed")
    step_drive = np.array([callback(t, 321) for t in times[:-1]]) * config["input_scale"]
    activation = config["gain"] * (states[:-1] @ pipeline.weights.T) + step_drive
    return dict(times_ms=times, states=states, body_ids=encoded.body_ids, frame_drive=drive,
                frame_timestamps_s=timestamps_s, centroids=centroids, global_channels=encoded.channels,
                mapping_sha256=digest(mapping), activation_clipped_fraction=float(np.mean(activation > config["clip_max"])),
                simulation_config=config, condition_id=mapping["condition_id"], seed=mapping["seed"])
