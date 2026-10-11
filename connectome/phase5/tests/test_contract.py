"""Regression coverage for Phase 5 validation and downstream interface."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
import pytest
import yaml
from connectome.scripts.phase5.config import load_config, validate_config
from connectome.scripts.phase5.generator import generate_stimulus, render_frame, compute_timestamps, compute_trajectory
from connectome.scripts.phase5.stimulus_io import save_stimulus, generate_metadata, config_hash
from connectome.scripts.phase5.loader import load_stimulus


@pytest.fixture
def c():
    return dict(stimulus_id="sample", stimulus_type="static", width=64, height=64,
                fps=20, duration_ms=500.0, background_intensity=10, object_intensity=200,
                initial_position=[32.0, 32.0], initial_radius=5.0, shape="circle",
                start_time_ms=0.0, random_seed=123)


@pytest.mark.parametrize("key,value", [
    ("width", 0), ("height", -1), ("width", 2.5), ("height", True), ("width", 100000),
    ("fps", 0), ("fps", -1), ("fps", float("nan")), ("fps", float("inf")), ("fps", "20"),
    ("duration_ms", 0), ("duration_ms", -1), ("duration_ms", .001), ("duration_ms", 1e300),
    ("duration_ms", 10**400), ("duration_ms", True), ("background_intensity", -1),
    ("object_intensity", 256), ("object_intensity", 1.5), ("background_intensity", False),
    ("initial_radius", -1), ("initial_radius", float("nan")), ("initial_radius", 1e300),
    ("initial_position", [1]), ("initial_position", [0, float("inf")]),
    ("initial_position", "0,0"), ("initial_position", [0, True]), ("initial_position", [1e300, 0]),
    ("random_seed", -1), ("random_seed", 1.5), ("random_seed", True), ("random_seed", 2**32),
    ("start_time_ms", -1), ("start_time_ms", float("nan")),
    ("stimulus_id", "../escape"), ("stimulus_id", ""), ("stimulus_id", "a/b"),
    ("stimulus_type", "encoder"), ("stimulus_type", []), ("shape", "square"),
    ("rendering_radius_tolerance", -1), ("typo", 1),
    ("speed_px_per_s", -1), ("motion_direction_deg", float("nan")),
    ("expansion_params", {"f_R": 1, "Z0": 5, "v": float("nan"), "t_onset_ms": 0})
])
def test_invalid_config(c, key, value):
    c[key] = value
    with pytest.raises(ValueError):
        generate_stimulus(c)


def test_defaults(c):
    del c["width"]; del c["height"]
    snapshot = validate_config(c)
    assert snapshot["width"] == snapshot["height"] == 256
    snapshot["initial_position"][0] = 100
    assert c["initial_position"][0] == 32
    frames, _ = generate_stimulus(c)
    assert frames.shape == (10, 256, 256)


def test_memory_budget(c):
    c.update(width=8192, height=8192, fps=10, duration_ms=1000)
    with pytest.raises(ValueError, match="memory budget"):
        generate_stimulus(c)
    c.update(width=1, height=1, fps=1e12)
    with pytest.raises(ValueError, match="Frame count"):
        generate_stimulus(c)


@pytest.mark.parametrize("bad", [None, [], "config", 12])
def test_config_mapping(tmp_path, bad):
    path = tmp_path / "invalid.yaml"
    path.write_text(yaml.safe_dump(bad))
    with pytest.raises(ValueError, match="mapping"):
        load_config(path)


@pytest.mark.parametrize("duration,fps,n", [(555, 20, 11), (1000, 29.97, 29), (500, 2, 1)])
def test_timestamps(c, duration, fps, n):
    c.update(duration_ms=duration, fps=fps)
    frames, ts = generate_stimulus(c)
    assert frames.shape == (n, 64, 64)
    assert ts.dtype == np.float64
    np.testing.assert_array_equal(ts, np.arange(n, dtype=np.float64) / fps)
    assert ts[-1] < duration / 1000


@pytest.mark.parametrize("direction,dx,dy", [(0, 1, 0), (90, 0, -1), (180, -1, 0), (270, 0, 1), (-90, 0, 1), (450, 0, -1)])
def test_directions(c, direction, dx, dy):
    c.update(stimulus_type="translating", speed_px_per_s=20, motion_direction_deg=direction)
    f, ts = generate_stimulus(c)
    y, x = np.where(f[-1] == 200)
    assert x.mean() == pytest.approx(32 + 9 * dx, abs=.01)
    assert y.mean() == pytest.approx(32 + 9 * dy, abs=.01)


def test_delayed_motion(c):
    c.update(stimulus_type="translating", start_time_ms=100, speed_px_per_s=20, motion_direction_deg=0)
    f, _ = generate_stimulus(c)
    np.testing.assert_array_equal(f[0], f[2])
    y, x = np.where(f[3] == 200)
    assert x.mean() == pytest.approx(33)
    c["start_time_ms"] = 10000
    f, _ = generate_stimulus(c)
    assert np.all(f == f[0])
    c.update(start_time_ms=0, speed_px_per_s=0)
    f, _ = generate_stimulus(c)
    assert np.all(f == f[0])


@pytest.mark.parametrize("key,value", [("speed_px_per_s", -1), ("speed_px_per_s", float("inf")),
                                      ("motion_direction_deg", float("nan")), ("speed_px_per_s", 1e300)])
def test_invalid_translation(c, key, value):
    c.update(stimulus_type="translating", speed_px_per_s=20, motion_direction_deg=0)
    c[key] = value
    with pytest.raises(ValueError):
        generate_stimulus(c)


def looming(c):
    c.update(stimulus_type="looming", expansion_params=dict(f_R=100, Z0=10, v=10, t_onset_ms=100))
    return c


def test_looming_exact(c):
    c = looming(c)
    f, ts = generate_stimulus(c)
    y, x = np.ogrid[:64, :64]
    expected_radius = 100 / (10 - 10 * np.maximum(0, ts - .1))
    _, radius = compute_trajectory(c)
    np.testing.assert_array_equal(radius, expected_radius)
    areas = []
    for frame, r in zip(f, expected_radius):
        expected = np.where((x - 32)**2 + (y - 32)**2 <= r*r, 200, 10).astype(np.uint8)
        np.testing.assert_array_equal(frame, expected)
        areas.append(np.count_nonzero(frame == 200))
    assert np.all(np.diff(areas) >= 0)
    np.testing.assert_array_equal(f[0], f[2])


@pytest.mark.parametrize("key,value", [("f_R", 0), ("f_R", -1), ("v", -1), ("v", float("nan")),
                                      ("Z0", 1), ("Z0", -1), ("t_onset_ms", -1),
                                      ("min_distance", 0), ("min_distance", -1), ("f_R", 1e300)])
def test_looming_constraints(c, key, value):
    c = looming(c); c["expansion_params"][key] = value
    with pytest.raises(ValueError):
        generate_stimulus(c)


def test_onset_after_duration(c):
    c = looming(c)
    c["expansion_params"].update(t_onset_ms=10000, v=10000)
    f, _ = generate_stimulus(c)
    assert np.all(f == f[0])
    c["expansion_params"].update(t_onset_ms=0, v=0)
    f, _ = generate_stimulus(c)
    assert np.all(f == f[0])


def test_old_fast_invalid(c):
    c = looming(c)
    c.update(duration_ms=1000)
    c["expansion_params"].update(Z0=50, v=80, t_onset_ms=200)
    with pytest.raises(ValueError, match="collision"):
        generate_stimulus(c)


def test_collision_boundary(c):
    c = looming(c)
    c["expansion_params"].update(Z0=5, v=8, t_onset_ms=0)
    with pytest.raises(ValueError, match="collision"):
        generate_stimulus(c)  # Z(duration)=1 even though last frame stays above 1.


@pytest.mark.parametrize("radius,pos,expected", [(0, [32, 32], "background"),
    (5, [-100, 32], "background"), (5, [32, 1000], "background"),
    (1e9, [32, 32], "object"), (5, [0, 0], "clipped")])
def test_edges(c, radius, pos, expected):
    c.update(initial_radius=radius, initial_position=pos)
    f, _ = generate_stimulus(c)
    if expected == "background": assert np.all(f == 10)
    elif expected == "object": assert np.all(f == 200)
    else:
        assert f[0, 0, 0] == 200
        assert f[0, -1, -1] == 10
        assert np.count_nonzero(f[0] == 200) < np.pi * 25


def test_equal_intensity_and_inverted_contrast(c):
    c.update(background_intensity=200, object_intensity=10)
    f, _ = generate_stimulus(c)
    assert f[0, 32, 32] == 10 and f[0, 0, 0] == 200
    c["object_intensity"] = 200
    f, _ = generate_stimulus(c)
    assert np.all(f == 200)


def test_entry_points():
    with pytest.raises(ValueError): render_frame(10, 10, 0, 256, 5, 5, 1)
    with pytest.raises(ValueError): render_frame(10, 10, 0, 255, 5, 5, -1)
    with pytest.raises(ValueError): compute_timestamps(1000, 0)


def test_metadata_contract(c, tmp_path):
    c = looming(c)
    f, ts = generate_stimulus(c)
    save_stimulus(tmp_path, c, f, ts)
    f2, ts2, m, snap = load_stimulus(tmp_path, "sample")
    np.testing.assert_array_equal(f, f2); np.testing.assert_array_equal(ts, ts2)
    assert m["schema_version"] == "1.0" and m["frame_layout"] == "THW"
    assert m["timestamps_s"] == ts.tolist()
    assert m["radius_px"][0] == 10
    assert m["units"]["v"] == "abstract distance/s"
    assert m["config_hash"] == config_hash(snap)
    assert m["run_date"].endswith("+00:00")
    assert yaml.safe_load((tmp_path / "sample_config.yaml").read_text()) == snap
    other = generate_metadata(c, f, ts)
    for k in ("config_hash", "frames_sha256", "timestamps_sha256"):
        assert m[k] == other[k]
    c["expansion_params"]["v"] = 0
    assert m["config_snapshot"]["expansion_params"]["v"] == 10


@pytest.mark.parametrize("field", ["schema_version", "config_hash", "n_frames", "timestamps_s", "radius_px", "frames", "timestamps", "snapshot", "stimulus_id", "run_date", "library_versions"])
def test_tampering(c, tmp_path, field):
    f, ts = generate_stimulus(c); save_stimulus(tmp_path, c, f, ts)
    path = tmp_path / "sample_metadata.json"
    meta = json.loads(path.read_text())
    if field == "frames":
        f[0, 0, 0] = 200
        np.savez_compressed(tmp_path / "sample.npz", frames=f, timestamps_s=ts)
    elif field == "timestamps":
        ts[-1] += .001
        np.savez_compressed(tmp_path / "sample.npz", frames=f, timestamps_s=ts)
    elif field == "snapshot":
        (tmp_path / "sample_config.yaml").write_text("fps: 99\n")
    else:
        meta[field] = "corrupt"
        path.write_text(json.dumps(meta))
    with pytest.raises(ValueError): load_stimulus(tmp_path, "sample")


def test_legacy(c, tmp_path):
    f, ts = generate_stimulus(c)
    np.savez_compressed(tmp_path / "sample.npz", frames=f, timestamps_s=ts)
    m = dict(stimulus_id="sample", config_snapshot=c, config_hash=config_hash(c))
    (tmp_path / "sample_metadata.json").write_text(json.dumps(m))
    with pytest.warns(UserWarning, match="Legacy"):
        f2, _, _, _ = load_stimulus(tmp_path, "sample")
    np.testing.assert_array_equal(f, f2)


def test_save_checks(c, tmp_path):
    f, ts = generate_stimulus(c)
    with pytest.raises(ValueError): save_stimulus(tmp_path, c, f.astype(float), ts)
    with pytest.raises(ValueError): save_stimulus(tmp_path, c, f, ts.astype(np.float32))
    assert list(tmp_path.iterdir()) == []
    save_stimulus(tmp_path, c, f, ts)
    with pytest.raises(FileExistsError): save_stimulus(tmp_path, c, f, ts)
    save_stimulus(tmp_path, c, f, ts, overwrite=True)
    load_stimulus(tmp_path, "sample")


def test_cli(c, tmp_path):
    path = tmp_path / "config.yaml"; path.write_text(yaml.safe_dump(c))
    root = Path(__file__).resolve().parents[3]
    command = [sys.executable, "-m", "connectome.scripts.phase5.run_stimulus", "--config", str(path), "--out-dir", str(tmp_path / "out")]
    run = subprocess.run(command, cwd=root, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    assert "Generated 10 frames" in run.stdout
    load_stimulus(tmp_path / "out", "sample")


def test_diagnostics(tmp_path):
    from connectome.scripts.phase5.diagnostics import run_diagnostics
    reports = tmp_path / "reports"; reports.mkdir()
    sentinel = reports / "unrelated.png"; sentinel.write_bytes(b"keep")
    summary = run_diagnostics(tmp_path)
    assert sentinel.read_bytes() == b"keep"
    assert len(summary["samples"]) == 7 and len(summary["plots"]) == 7
    for row in summary["samples"]:
        assert row["exact_round_trip"] and row["shape"] == [60, 256, 256]
    for name in summary["plots"]:
        assert (reports / name).stat().st_size > 1000


def test_report_evidence(tmp_path, monkeypatch):
    from connectome.scripts.phase5 import generate_report
    monkeypatch.setattr(generate_report, "PHASE5", tmp_path)
    results = tmp_path / "results"; results.mkdir()
    evidence = dict(validated_at="2026-10-11T00:00:00+00:00", test_command="pytest",
        test_exit_code=0, test_counts=dict(tests=7, failures=0, errors=0, skipped=0),
        protected_file_count=66, protected_files_unchanged=True, sample_count=7, plot_count=7)
    path = results / "validation_results.json"
    path.write_text(json.dumps(evidence))
    generate_report.regenerate_report()
    assert "7 passed, 0 failures" in (tmp_path / "phase5_validation_report.md").read_text()
    evidence["test_counts"]["failures"] = 1
    path.write_text(json.dumps(evidence))
    with pytest.raises(ValueError, match="does not support completion"):
        generate_report.regenerate_report()
