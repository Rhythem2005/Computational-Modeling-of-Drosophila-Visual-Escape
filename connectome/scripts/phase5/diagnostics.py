import os
import time
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

import sys
sys.path.insert(0, '.')
from connectome.scripts.phase5 import config, generator, stimulus_io

def measure_radius(frame, bg, obj):
    area = np.sum(frame == obj)
    return np.sqrt(area / np.pi)

def clear_old_pngs(report_dir: Path):
    for f in report_dir.glob("*.png"):
        f.unlink()

def run_diagnostics():
    report_dir = Path("connectome/phase5/reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    clear_old_pngs(report_dir)
    
    print("="*60)
    print("STIMULUS DIAGNOSTICS")
    print("="*60)
    
    # Base config
    base_config = {
        "stimulus_id": "diag_looming",
        "stimulus_type": "looming",
        "width": 256,
        "height": 256,
        "fps": 60,
        "duration_ms": 1000.0,
        "background_intensity": 0,
        "object_intensity": 255,
        "initial_position": [128.0, 128.0],
        "initial_radius": 10.0,
        "shape": "circle",
        "start_time_ms": 0.0,
        "random_seed": 42,
        "expansion_params": {
            "f_R": 100.0,
            "Z0": 50.0,
            "v": 40.0,
            "t_onset_ms": 200.0
        }
    }
    
    # 1. Looming (Reference)
    frames, ts = generator.generate_stimulus(base_config)
    radii = [measure_radius(f, 0, 255) for f in frames]
    t_onset = 0.2
    Z_t = np.maximum(1e-5, base_config["expansion_params"]["Z0"] - base_config["expansion_params"]["v"] * (ts - t_onset))
    analytic = np.where(ts > t_onset, base_config["expansion_params"]["f_R"] / Z_t, base_config["expansion_params"]["f_R"] / base_config["expansion_params"]["Z0"])
    
    plt.figure()
    plt.plot(ts, analytic, label='Analytic r(t)')
    plt.plot(ts, radii, '--', label='Measured (px)')
    plt.legend()
    plt.title("Looming: Radius vs Time")
    plt.savefig(report_dir / "looming_radius.png")
    plt.close()
    
    # Montage looming
    idx = [0, 15, 30, 45, 59]
    fig, axes = plt.subplots(1, 5, figsize=(15,3))
    for i, ax in zip(idx, axes):
        ax.imshow(frames[i], cmap='gray', vmin=0, vmax=255)
        ax.set_title(f"t={ts[i]:.2f}s")
        ax.axis('off')
    plt.savefig(report_dir / "looming_montage.png")
    plt.close()
    
    # 2. Matched Static Control
    c_static = base_config.copy()
    c_static["stimulus_type"] = "control_static"
    c_static["initial_radius"] = base_config["expansion_params"]["f_R"] / base_config["expansion_params"]["Z0"]
    sf, _ = generator.generate_stimulus(c_static)
    
    plt.figure()
    plt.imshow(sf[0], cmap='gray', vmin=0, vmax=255)
    plt.title("Static Control Frame")
    plt.savefig(report_dir / "static_control.png")
    plt.close()
    
    # 3. Fast Expansion
    c_fast = base_config.copy()
    c_fast["expansion_params"] = {**base_config["expansion_params"], "v": 80.0} # faster
    ff, ft = generator.generate_stimulus(c_fast)
    f_radii = [measure_radius(f, 0, 255) for f in ff]
    
    plt.figure()
    plt.plot(ts, radii, label='Slow (v=40)')
    plt.plot(ft, f_radii, label='Fast (v=80)')
    plt.legend()
    plt.title("Looming: Slow vs Fast")
    plt.savefig(report_dir / "looming_speed_comparison.png")
    plt.close()
    
    # 4. Translation Montage
    c_trans = base_config.copy()
    c_trans["stimulus_type"] = "translating"
    c_trans["initial_radius"] = 15.0
    c_trans["motion_direction_deg"] = 45.0
    c_trans["speed_px_per_s"] = 100.0
    tf, tt = generator.generate_stimulus(c_trans)
    
    fig, axes = plt.subplots(1, 5, figsize=(15,3))
    for i, ax in zip(idx, axes):
        ax.imshow(tf[i], cmap='gray', vmin=0, vmax=255)
        ax.set_title(f"t={tt[i]:.2f}s")
        ax.axis('off')
    plt.savefig(report_dir / "translation_montage.png")
    plt.close()
    
    # 5. Looming vs Matched Static Control Radius Comparison
    static_radii = [measure_radius(f, 0, 255) for f in sf]
    plt.figure()
    plt.plot(ts, radii, label='Looming')
    plt.plot(ts, static_radii, '--', label='Matched Static Control')
    plt.legend()
    plt.title("Looming vs Static Control: Radius over Time")
    plt.savefig(report_dir / "looming_vs_static.png")
    plt.close()

    print("\nGenerated PNG files:")
    for f in report_dir.glob("*.png"):
        mtime = time.ctime(os.path.getmtime(f))
        print(f"  {f.name} - modified: {mtime}")

if __name__ == "__main__":
    run_diagnostics()
