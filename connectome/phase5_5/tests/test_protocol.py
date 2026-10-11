"""Protocol integrity tests: no encoder, neural simulation, or outcome fitting."""
from copy import deepcopy
import numpy as np
import pytest
from connectome.scripts.phase5_5.protocol import (
    load_design, validate_design, build_manifest, validate_manifest,
    digest, content_fingerprint,
)
from connectome.scripts.phase5.generator import generate_stimulus


@pytest.fixture(scope="module")
def design():
    return load_design()


@pytest.fixture(scope="module")
def manifest(design):
    return build_manifest(design)


def test_counts_and_split_integrity(manifest, design):
    counts = validate_manifest(manifest, design)
    assert len(manifest["scenarios"]) == 1024
    assert sum(x["families"] for x in counts.values()) == 256
    assert sum(x["label"] for x in manifest["scenarios"]) == 256
    assert sum(x["split"] == "test" for x in manifest["scenarios"]) == 640


def test_deterministic(manifest, design):
    assert digest(build_manifest(design)) == digest(manifest)


def test_seed_changes_configs(manifest, design):
    d = deepcopy(design)
    d["seed"] += 1
    assert build_manifest(d)["scenarios"][0]["content_sha256"] != manifest["scenarios"][0]["content_sha256"]


def test_other_cohort_count_does_not_change_train(manifest, design):
    d = deepcopy(design)
    d["cohorts"]["validation"]["groups"] += 1
    assert [x for x in build_manifest(d)["scenarios"] if x["split"] == "train"] == [x for x in manifest["scenarios"] if x["split"] == "train"]


@pytest.mark.parametrize("section,key,value", [
    (None,"seed",-1), (None,"protocol_version","2.0"),
    (None,"input_allowlist",["frames","label"]),
    ("rendering","fps",0), ("rendering","duration_ms",-1),
    ("rendering","onset_ms",1000), ("rendering","Z0",float("nan")),
    ("rendering","center_min_px",-10), ("rendering","translation_speed_range_px_s",[0,40]),
    ("rendering","translation_speed_range_px_s",[15,1e9]),
    ("rendering","background_intensity",0), ("rendering","width",256.5),
    ("evaluation","bootstrap_resamples",0), ("evaluation","sustained_threshold_ms",-20),
    ("evaluation","input_mapping_seeds",[1,1]), ("evaluation","nn_learning_rates",[-1]),
    ("evaluation","fixed_gain",1), ("evaluation","primary_mapping","retinotopic"),
    ("evaluation","primary_comparison_ci_level",.95),
    ("evaluation","clipping_fraction_limit",float("nan")),
])
def test_reject_invalid_design(design, section, key, value):
    d = deepcopy(design)
    target = d if section is None else d[section]
    target[key] = value
    with pytest.raises(ValueError):
        validate_design(d)


@pytest.mark.parametrize("key,value", [("groups",0), ("split","test"), ("radius_range_px",[0,16]), ("growth_fraction_range",[.5,1]), ("contrast_range",[1,128]), ("contrast_range",[1.5,32])])
def test_reject_invalid_cohort(design, key, value):
    d = deepcopy(design)
    d["cohorts"]["train"][key] = value
    with pytest.raises(ValueError):
        validate_design(d)


def test_ood_must_be_disjoint(design):
    d = deepcopy(design)
    d["cohorts"]["test_ood_size"]["radius_range_px"] = [9,15]
    with pytest.raises(ValueError, match="OOD"):
        validate_design(d)


@pytest.mark.parametrize("kind", ["hash", "label", "split", "identity", "count", "matched", "range"])
def test_reject_corrupt_manifest(manifest, design, kind):
    m = deepcopy(manifest)
    row = m["scenarios"][0]
    if kind == "hash": row["config_sha256"] = "bad"
    elif kind == "label": row["label"] = 0
    elif kind == "split": row["split"] = "test"
    elif kind == "identity": m["protocol_id"] = "wrong"
    elif kind == "count": m["scenarios"].pop()
    else:
        row = m["scenarios"][1] if kind == "matched" else row
        row["config"]["initial_position"] = [100,101] if kind == "matched" else [1,2]
        row["config_sha256"] = digest(row["config"])
        row["content_sha256"] = content_fingerprint(row["config"])
    with pytest.raises(ValueError):
        validate_manifest(m, design)


@pytest.mark.parametrize("cohort", ["train","validation","test_id","test_ood_size","test_ood_growth","test_ood_contrast"])
def test_rendered_matched_controls(manifest, cohort):
    rows = [x for x in manifest["scenarios"] if x["group_id"] == f"{cohort}_f0000"]
    movies = {r["role"]: generate_stimulus(r["config"])[0] for r in rows}
    np.testing.assert_array_equal(movies["looming"][0], movies["static_initial"][0])
    np.testing.assert_array_equal(movies["looming"][-1], movies["static_terminal"][-1])
    assert not np.array_equal(movies["looming"][-1], movies["looming"][0])
    assert not np.array_equal(movies["translating_initial"][-1], movies["translating_initial"][0])
    for r in rows:
        frames, ts = generate_stimulus(r["config"])
        assert frames.shape == (60,256,256) and frames.dtype == np.uint8
        np.testing.assert_array_equal(ts, np.arange(60, dtype=np.float64)/60)
        assert set(np.unique(frames)) == {128,r["config"]["object_intensity"]}
        if r["role"].startswith("static"):
            assert np.all(frames == frames[0])
        if r["role"] == "looming":
            area = np.sum(frames != 128, axis=(1,2))
            assert np.all(np.diff(area.astype(float)) >= 0)
            assert np.all(area[:13] == area[0])
