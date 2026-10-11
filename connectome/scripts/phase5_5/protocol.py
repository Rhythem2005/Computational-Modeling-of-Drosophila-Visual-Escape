"""Validate research design and build scenario configs, not neural responses."""
import hashlib
import json
from pathlib import Path
import numpy as np
import yaml
from connectome.scripts.phase5.config import validate_config
from connectome.scripts.phase5.generator import compute_timestamps

ROOT = Path(__file__).resolve().parents[3]
PHASE = ROOT / "connectome" / "phase5_5"
ROLES = ["looming", "static_initial", "static_terminal", "translating_initial"]
COHORTS = ["train", "validation", "test_id", "test_ood_size", "test_ood_growth", "test_ood_contrast"]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def load_design(path=PHASE / "benchmark_design.yaml"):
    design = yaml.safe_load(Path(path).read_text())
    validate_design(design)
    return design


def validate_design(d):
    if not isinstance(d, dict) or d.get("protocol_version") != "1.0":
        raise ValueError("Expected research protocol version 1.0")
    if d.get("protocol_id") != "fly_open_loop_v1" or d.get("primary_task") != "open_loop_looming_response":
        raise ValueError("Unsupported protocol task")
    if d.get("input_allowlist") != ["frames", "timestamps_s"] or d.get("frame_schema_version") != "1.0":
        raise ValueError("Encoder allowlist must exclude labels and generator metadata")
    if d.get("family_roles") != ROLES or set(d.get("cohorts", {})) != set(COHORTS):
        raise ValueError("Expected matched controls and six disjoint cohorts")
    if type(d.get("seed")) is not int or not 0 <= d["seed"] <= 2**32 - 1:
        raise ValueError("Invalid design seed")
    r = d["rendering"]
    for key in ("width", "height", "fps", "duration_ms", "Z0", "min_distance"):
        if isinstance(r[key], bool) or not np.isfinite(r[key]) or r[key] <= 0:
            raise ValueError(f"Invalid rendering {key}")
    if any(type(r[k]) is not int for k in ("width", "height", "background_intensity")):
        raise ValueError("Resolution and background must be integers")
    if r["background_intensity"] != 128:
        raise ValueError("Version 1 contrast design requires background 128")
    speed_lo, speed_hi = r["translation_speed_range_px_s"]
    if not 0 < speed_lo < speed_hi or not r["translation_directions_deg"]:
        raise ValueError("Invalid translation range")
    if not all(np.isfinite(x) and 0 <= x < 360 for x in r["translation_directions_deg"]):
        raise ValueError("Invalid translation direction")
    if not 0 < r["onset_ms"] < r["duration_ms"]:
        raise ValueError("Observation onset must be inside duration")
    if r["center_min_px"] >= r["center_max_px"]:
        raise ValueError("Invalid center range")
    for name, c in d["cohorts"].items():
        expected_split = name if name in {"train", "validation"} else "test"
        if c["split"] != expected_split or type(c["groups"]) is not int or c["groups"] < 1:
            raise ValueError("Invalid split or family count")
        a, b = c["radius_range_px"]
        q0, q1 = c["growth_fraction_range"]
        lo, hi = c["contrast_range"]
        if not 0 < a < b or not 0 < q0 < q1 < 1 or not 0 < lo <= hi <= 127:
            raise ValueError("Invalid radius, growth or contrast range")
        if type(lo) is not int or type(hi) is not int:
            raise ValueError("Contrast limits must be integers")
        margin = max(b / (1 - q1), b + speed_hi * (r["duration_ms"] - r["onset_ms"]) / 1000)
        if r["center_min_px"] < margin or r["center_max_px"] + margin > min(r["width"], r["height"]):
            raise ValueError("Benchmark must keep entire objects inside the image")
        if r["Z0"] * (1 - q1) <= r["min_distance"]:
            raise ValueError("Growth range reaches looming distance margin")
    for ood, key in [("test_ood_size", "radius_range_px"), ("test_ood_growth", "growth_fraction_range"), ("test_ood_contrast", "contrast_range")]:
        lo, hi = d["cohorts"][ood][key]
        train_lo, train_hi = d["cohorts"]["train"][key]
        if not (hi < train_lo or lo > train_hi):
            raise ValueError("OOD ranges must be disjoint from training on their named axis")
    e = d["evaluation"]
    for key in ("bootstrap_resamples", "shuffled_networks_per_control", "nn_hidden_units", "nn_max_epochs", "nn_early_stopping_patience"):
        if type(e[key]) is not int or e[key] < 1:
            raise ValueError(f"Invalid evaluation {key}")
    for key in ("validation_fpr_target", "practical_test_tpr_target", "practical_test_fpr_limit", "meaningful_balanced_accuracy_difference", "clipping_fraction_limit", "practical_generalization_gap_limit", "hypothesis_h1_ci_level"):
        if not np.isfinite(e[key]) or not 0 < e[key] < 1:
            raise ValueError(f"Invalid evaluation {key}")
    if not 0 < e["sustained_threshold_ms"] < r["duration_ms"] - r["onset_ms"]:
        raise ValueError("Invalid threshold persistence")
    if not 0 < e["secondary_spectral_radius_target"] < 1:
        raise ValueError("Invalid spectral-radius target")
    for key in ("input_mapping_seeds", "nn_training_seeds"):
        if not e[key] or len(set(e[key])) != len(e[key]) or any(type(x) is not int or not 0 <= x < 2**32 for x in e[key]):
            raise ValueError("Invalid or duplicate evaluation seeds")
    if type(e["bootstrap_seed"]) is not int or not 0 <= e["bootstrap_seed"] < 2**32:
        raise ValueError("Invalid bootstrap seed")
    if not e["nn_learning_rates"] or not all(np.isfinite(x) and x > 0 for x in e["nn_learning_rates"]):
        raise ValueError("Invalid learning rate")
    if e["observation_window_s"] != [r["onset_ms"] / 1000, r["duration_ms"] / 1000]:
        raise ValueError("Evaluation window must match stimulus timing")
    if e["primary_mapping"] != "uniform_population":
        raise ValueError("Primary mapping must avoid unavailable retinotopy")
    if len(e["input_mapping_seeds"]) != len(set(e["input_mapping_seeds"])):
        raise ValueError("Mapping seeds must be distinct")
    if (e["fixed_gain"], e["fixed_tau_ms"], e["fixed_input_scale"]) != (.5, 10.0, .4):
        raise ValueError("Primary simulator parameters must match Phase 4 defaults")
    if e["threshold_candidate_limit"] != 32 or e["primary_comparison_ci_level"] != .975:
        raise ValueError("Threshold budget and primary multiplicity correction must be explicit")


def content_fingerprint(config):
    return digest({k: v for k, v in config.items() if k not in {"stimulus_id", "random_seed"}})


def build_manifest(design):
    validate_design(design)
    r = design["rendering"]
    last_t = compute_timestamps(r["duration_ms"], r["fps"])[-1]
    rows = []
    for cohort, spec in design["cohorts"].items():
        cohort_key = int(hashlib.sha256(cohort.encode()).hexdigest()[:8], 16)
        for index in range(spec["groups"]):
            rng = np.random.default_rng(np.random.SeedSequence([design["seed"], cohort_key, index]))
            radius = float(rng.uniform(*spec["radius_range_px"]))
            growth = float(rng.uniform(*spec["growth_fraction_range"]))
            contrast = int(rng.integers(spec["contrast_range"][0], spec["contrast_range"][1] + 1))
            sign = int(rng.choice([-1, 1]))
            obj = r["background_intensity"] + sign * contrast
            center = rng.uniform(r["center_min_px"], r["center_max_px"], size=2).tolist()
            speed = float(rng.uniform(*r["translation_speed_range_px_s"]))
            direction = int(rng.choice(r["translation_directions_deg"]))
            active_seconds = (r["duration_ms"] - r["onset_ms"]) / 1000
            velocity = growth * r["Z0"] / active_seconds
            terminal_radius = radius / (1 - growth * (last_t - r["onset_ms"] / 1000) / active_seconds)
            group = f"{cohort}_f{index:04d}"
            for role in ROLES:
                config = dict(stimulus_id=f"{group}_{role}", stimulus_type="looming" if role == "looming" else "translating" if role == "translating_initial" else "static",
                    width=r["width"], height=r["height"], fps=r["fps"], duration_ms=r["duration_ms"],
                    background_intensity=r["background_intensity"], object_intensity=obj,
                    initial_position=center, initial_radius=terminal_radius if role == "static_terminal" else radius,
                    shape="circle", start_time_ms=r["onset_ms"], random_seed=design["seed"])
                if role == "looming":
                    config["expansion_params"] = dict(f_R=radius*r["Z0"], Z0=r["Z0"], v=velocity,
                        t_onset_ms=r["onset_ms"], min_distance=r["min_distance"])
                if role == "translating_initial":
                    config.update(speed_px_per_s=speed, motion_direction_deg=direction)
                config = validate_config(config)
                rows.append(dict(scenario_id=config["stimulus_id"], group_id=group,
                    split=spec["split"], cohort=cohort, role=role, label=int(role == "looming"),
                    label_semantics="synthetic radial expansion, not physical collision",
                    config=config, config_sha256=digest(config), content_sha256=content_fingerprint(config)))
    manifest = dict(schema_version="1.0", protocol_id=design["protocol_id"],
        design_sha256=digest(design), seed=design["seed"],
        status="planned_scenarios_only_no_neural_results", scenarios=rows)
    validate_manifest(manifest, design)
    return manifest


def validate_manifest(manifest, design):
    validate_design(design)
    if manifest.get("protocol_id") != design["protocol_id"] or manifest.get("seed") != design["seed"] or manifest.get("status") != "planned_scenarios_only_no_neural_results":
        raise ValueError("Manifest identity or status mismatch")
    if manifest.get("schema_version") != "1.0" or manifest.get("design_sha256") != digest(design):
        raise ValueError("Manifest version or design hash mismatch")
    rows = manifest["scenarios"]
    expected_count = sum(c["groups"] for c in design["cohorts"].values()) * len(ROLES)
    if len(rows) != expected_count:
        raise ValueError("Incorrect scenario count")
    ids, fingerprints, groups, counts = set(), set(), {}, {}
    for row in rows:
        c = validate_config(row["config"])
        if row["scenario_id"] != c["stimulus_id"] or row["scenario_id"] in ids:
            raise ValueError("Duplicate or inconsistent scenario ID")
        ids.add(row["scenario_id"])
        fp = content_fingerprint(c)
        if fp != row["content_sha256"] or digest(c) != row["config_sha256"] or fp in fingerprints:
            raise ValueError("Duplicate content or incorrect config fingerprint")
        fingerprints.add(fp)
        cohort = row["cohort"]
        if cohort not in design["cohorts"] or row["split"] != design["cohorts"][cohort]["split"]:
            raise ValueError("Split leakage or unknown cohort")
        role = row["role"]
        if role not in ROLES or row["label"] != int(role == "looming"):
            raise ValueError("Incorrect role or label")
        expected_type = "looming" if role == "looming" else "translating" if role == "translating_initial" else "static"
        if c["stimulus_type"] != expected_type:
            raise ValueError("Role and stimulus type disagree")
        group = groups.setdefault(row["group_id"], [])
        if group and (group[0]["cohort"] != cohort or group[0]["split"] != row["split"]):
            raise ValueError("Matched family crosses split/cohort boundary")
        group.append(row)
        counts[cohort] = counts.get(cohort, 0) + 1
    for cohort, spec in design["cohorts"].items():
        if counts.get(cohort) != spec["groups"] * len(ROLES):
            raise ValueError("Cohort size mismatch")
    for group in groups.values():
        if sorted(x["role"] for x in group) != sorted(ROLES):
            raise ValueError("Incomplete or duplicate family roles")
        by_role = {x["role"]: x["config"] for x in group}
        loom = by_role["looming"]
        spec = design["cohorts"][group[0]["cohort"]]
        rendering = design["rendering"]
        ep = loom["expansion_params"]
        growth = ep["v"] * (rendering["duration_ms"] - rendering["onset_ms"]) / 1000 / ep["Z0"]
        for value, limits in ((loom["initial_radius"], spec["radius_range_px"]), (growth, spec["growth_fraction_range"]), (abs(loom["object_intensity"]-loom["background_intensity"]), spec["contrast_range"])):
            if not limits[0] <= value <= limits[1]:
                raise ValueError("Scenario outside declared cohort range")
        for key in ("width", "height", "fps", "duration_ms", "background_intensity"):
            if loom[key] != rendering[key]:
                raise ValueError("Scenario rendering differs from design")
        if loom["start_time_ms"] != rendering["onset_ms"] or ep["t_onset_ms"] != rendering["onset_ms"] or ep["Z0"] != rendering["Z0"] or ep["min_distance"] != rendering["min_distance"]:
            raise ValueError("Scenario geometry or timing differs from design")
        if not all(rendering["center_min_px"] <= x <= rendering["center_max_px"] for x in loom["initial_position"]):
            raise ValueError("Scenario center outside range")
        translation = by_role["translating_initial"]
        if not rendering["translation_speed_range_px_s"][0] <= translation["speed_px_per_s"] <= rendering["translation_speed_range_px_s"][1] or translation["motion_direction_deg"] not in rendering["translation_directions_deg"]:
            raise ValueError("Scenario translation outside design")
        for c in by_role.values():
            for key in ("initial_position", "object_intensity", "background_intensity", "fps", "duration_ms", "width", "height", "start_time_ms", "random_seed", "shape"):
                if c[key] != loom[key]:
                    raise ValueError("Matched family attributes differ")
        initial_radius = loom["expansion_params"]["f_R"] / loom["expansion_params"]["Z0"]
        for role in ("static_initial", "translating_initial"):
            if not np.isclose(by_role[role]["initial_radius"], initial_radius, rtol=1e-12, atol=0):
                raise ValueError("Initial size control is not matched")
        last_t = compute_timestamps(loom["duration_ms"], loom["fps"])[-1]
        ep = loom["expansion_params"]
        terminal = ep["f_R"] / (ep["Z0"] - ep["v"] * max(0, last_t-ep["t_onset_ms"]/1000))
        if not np.isclose(by_role["static_terminal"]["initial_radius"], terminal, rtol=1e-12, atol=0):
            raise ValueError("Terminal size control is not matched")
    return {name: {"families": spec["groups"], "episodes": counts[name]} for name, spec in design["cohorts"].items()}
