"""Generate valid saved samples and headless diagnostic plots."""
from copy import deepcopy
import json
from pathlib import Path
import sys
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from connectome.scripts.phase5 import generator, stimulus_io, loader

PHASE5 = Path(__file__).resolve().parents[2] / "phase5"


def measure_radius(frame, bg, obj):
    if bg == obj:
        raise ValueError("Cannot measure object area at zero contrast")
    return np.sqrt(np.count_nonzero(frame == obj) / np.pi)


def sample_configs():
    base = dict(stimulus_id="diag_looming", stimulus_type="looming", width=256,
        height=256, fps=60, duration_ms=1000.0, background_intensity=0,
        object_intensity=255, initial_position=[128.0, 128.0], initial_radius=12.0,
        shape="circle", start_time_ms=0.0, random_seed=42,
        expansion_params=dict(f_R=600.0, Z0=50.0, v=40.0, t_onset_ms=200.0))
    configs = [base]
    for sid, stype in [("diag_fast", "looming"), ("diag_static", "static"),
                       ("diag_control_static", "control_static"),
                       ("diag_translation", "translating"),
                       ("diag_control_translation", "control_translating"),
                       ("diag_background", "control_background")]:
        c = deepcopy(base)
        c.update(stimulus_id=sid, stimulus_type=stype)
        if sid == "diag_fast":
            c["expansion_params"]["v"] = 55.0
        elif stype != "looming":
            c.pop("expansion_params")
        if stype in {"translating", "control_translating"}:
            c.update(initial_position=[64.0, 192.0], initial_radius=15.0,
                     speed_px_per_s=100.0, motion_direction_deg=45.0)
        configs.append(c)
    return configs


def run_diagnostics(output_root=None):
    root = PHASE5 if output_root is None else Path(output_root)
    reports, samples = root / "reports", root / "results" / "samples"
    reports.mkdir(parents=True, exist_ok=True)
    runs, summary = {}, []
    for c in sample_configs():
        frames, ts = generator.generate_stimulus(c)
        stimulus_io.save_stimulus(samples, c, frames, ts, overwrite=True)
        loaded, times, meta, snap = loader.load_stimulus(samples, c["stimulus_id"])
        if not np.array_equal(frames, loaded) or not np.array_equal(ts, times):
            raise AssertionError("Saved sample failed exact round trip")
        centers, radii = generator.compute_trajectory(snap)
        measured = np.array([measure_radius(f, 0, 255) for f in frames])
        row = dict(stimulus_id=c["stimulus_id"], stimulus_type=c["stimulus_type"],
                   shape=list(frames.shape), dtype=str(frames.dtype),
                   first_timestamp_s=float(ts[0]), last_timestamp_s=float(ts[-1]),
                   first_radius_px=float(radii[0]), last_radius_px=float(radii[-1]),
                   frames_sha256=meta["frames_sha256"], config_hash=meta["config_hash"],
                   exact_round_trip=True)
        if c["stimulus_type"] == "looming":
            error = float(np.max(np.abs(measured - radii)))
            if error > 1 or np.any(np.diff(measured) < 0):
                raise AssertionError("Looming radius rasterization or monotonicity failed")
            row["max_radius_error_px"] = error
        if c["stimulus_type"] in {"translating", "control_translating"}:
            centroids = np.array([[np.where(f == 255)[1].mean(), np.where(f == 255)[0].mean()] for f in frames])
            error = float(np.max(np.abs(centroids - centers)))
            if error > 1:
                raise AssertionError("Translation centroid differs from analytic trajectory")
            row["max_centroid_error_px"] = error
        summary.append(row)
        runs[c["stimulus_id"]] = (frames, ts, radii, measured, centers)

    plots = []
    def finish(name):
        plt.tight_layout()
        plt.savefig(reports / name, dpi=140)
        plt.close()
        plots.append(name)

    frames, ts, radius, measured, _ = runs["diag_looming"]
    plt.figure()
    plt.plot(ts, radius, label="Analytic pinhole radius")
    plt.plot(ts, measured, "--", label="Area-equivalent raster radius")
    plt.xlabel("Time (s)"); plt.ylabel("Radius (px)"); plt.legend()
    finish("looming_radius.png")
    for sid, name in [("diag_looming", "looming_montage.png"), ("diag_translation", "translation_montage.png")]:
        f, t, _, _, _ = runs[sid]
        indices = np.linspace(0, len(t) - 1, 5, dtype=int)
        fig, axes = plt.subplots(1, 5, figsize=(13, 3))
        for i, ax in zip(indices, axes):
            ax.imshow(f[i], cmap="gray", vmin=0, vmax=255)
            ax.set_title(f"{t[i]:.3f} s"); ax.axis("off")
        finish(name)
    plt.figure()
    plt.imshow(runs["diag_static"][0][0], cmap="gray", vmin=0, vmax=255)
    plt.title("Matched static: radius 12 px"); plt.xlabel("x (px)"); plt.ylabel("y (px)")
    finish("static_control.png")
    plt.figure()
    for sid, label in [("diag_looming", "v=40 abstract distance/s"), ("diag_fast", "v=55 abstract distance/s")]:
        _, t, _, m, _ = runs[sid]
        plt.plot(t, m, label=label)
    plt.xlabel("Time (s)"); plt.ylabel("Raster radius (px)"); plt.legend()
    finish("looming_speed_comparison.png")
    plt.figure()
    plt.plot(ts, measured, label="Looming")
    plt.plot(ts, runs["diag_static"][3], "--", label="Matched static")
    plt.xlabel("Time (s)"); plt.ylabel("Raster radius (px)"); plt.legend()
    finish("looming_vs_static.png")
    plt.figure()
    _, t, _, _, centers = runs["diag_translation"]
    plt.plot(t, centers[:, 0], label="x (px)")
    plt.plot(t, centers[:, 1], label="y (px)")
    plt.xlabel("Time (s)"); plt.ylabel("Center (px)"); plt.legend()
    finish("translation_trajectory.png")
    evidence = dict(samples=summary, plots=plots)
    (root / "results" / "sample_verification.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"Verified {len(summary)} samples by exact round trip; generated {len(plots)} plots.")
    return evidence


if __name__ == "__main__":
    run_diagnostics()
