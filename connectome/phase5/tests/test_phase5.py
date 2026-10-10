import pytest
import numpy as np
from pathlib import Path
import json

from connectome.scripts.phase5 import config, generator, stimulus_io, loader

@pytest.fixture
def base_config():
    return {
        "stimulus_id": "test_stim",
        "stimulus_type": "static",
        "width": 64,
        "height": 64,
        "fps": 30,
        "duration_ms": 500.0,
        "background_intensity": 10,
        "object_intensity": 200,
        "initial_position": [32.0, 32.0],
        "initial_radius": 5.0,
        "shape": "circle",
        "start_time_ms": 0.0,
        "random_seed": 123
    }

def test_validation_missing_fields(base_config, tmp_path):
    conf = base_config.copy()
    del conf["fps"]
    p = tmp_path / "c.yaml"
    import yaml
    with open(p, 'w') as f:
        yaml.dump(conf, f)
    
    with pytest.raises(ValueError, match="Missing required config field: fps"):
        config.load_config(p)

def test_validation_bad_dims(base_config, tmp_path):
    conf = base_config.copy()
    conf["width"] = 0
    p = tmp_path / "c.yaml"
    import yaml
    with open(p, 'w') as f: yaml.dump(conf, f)
    with pytest.raises(ValueError, match="Dimensions must be positive"):
        config.load_config(p)

def test_validation_bad_duration(base_config, tmp_path):
    conf = base_config.copy()
    conf["duration_ms"] = -10
    p = tmp_path / "c.yaml"
    import yaml
    with open(p, 'w') as f: yaml.dump(conf, f)
    with pytest.raises(ValueError, match="Duration must be positive"):
        config.load_config(p)

def test_validation_bad_geometry(base_config, tmp_path):
    conf = base_config.copy()
    conf["shape"] = "square"
    p = tmp_path / "c.yaml"
    import yaml
    with open(p, 'w') as f: yaml.dump(conf, f)
    with pytest.raises(ValueError, match="Only 'circle' shape is supported"):
        config.load_config(p)

def test_validation_looming_trajectory(base_config, tmp_path):
    conf = base_config.copy()
    conf["stimulus_type"] = "looming"
    # Z_end = Z0 - v*(dur - t_onset)
    # dur=0.5, t_onset=0.0 -> dt=0.5
    # v=20 -> dZ=10. Z0=10 -> Z_end=0.0 (collision)
    conf["expansion_params"] = {"f_R": 10.0, "Z0": 10.0, "v": 20.0, "t_onset_ms": 0.0}
    
    p = tmp_path / "c.yaml"
    import yaml
    with open(p, 'w') as f: yaml.dump(conf, f)
    with pytest.raises(ValueError, match="collision|negative distance"):
        config.load_config(p)

def test_rendering_properties(base_config):
    frames, ts = generator.generate_stimulus(base_config)
    assert frames.dtype == np.uint8
    assert frames.shape == (15, 64, 64)
    assert len(ts) == 15
    assert np.all((frames == 10) | (frames == 200))
    # Static unchanged across frames
    assert np.all(frames[0] == frames[-1])

def measure_radius(frame, bg, obj):
    area = np.sum(frame == obj)
    return np.sqrt(area / np.pi)

def test_translation(base_config):
    conf = base_config.copy()
    conf["stimulus_type"] = "translating"
    conf["motion_direction_deg"] = 0.0 # pure right
    conf["speed_px_per_s"] = 30.0 # 1 px per frame at 30 fps
    
    frames, ts = generator.generate_stimulus(conf)
    
    # Measure centroid
    def get_cx(frame):
        Y, X = np.where(frame == 200)
        return np.mean(X) if len(X)>0 else -1
        
    c0 = get_cx(frames[0])
    c_last = get_cx(frames[-1])
    
    # 14 frames elapsed = 14/30 s = 14 px
    disp = c_last - c0
    assert abs(disp - 14.0) <= 1.0 # Tolerance 1px

def test_control_background(base_config):
    conf = base_config.copy()
    conf["stimulus_type"] = "control_background"
    frames, ts = generator.generate_stimulus(conf)
    assert np.all(frames == 10)

def test_looming_trajectory(base_config):
    conf = base_config.copy()
    conf["stimulus_type"] = "looming"
    conf["expansion_params"] = {"f_R": 100.0, "Z0": 50.0, "v": 40.0, "t_onset_ms": 100.0}
    frames, ts = generator.generate_stimulus(conf)
    
    radii = [measure_radius(f, 10, 200) for f in frames]
    
    # Non-decreasing
    assert all(radii[i] <= radii[i+1] + 1.0 for i in range(len(radii)-1)) # +1.0 for discretization margin
    
    # Compare with analytic at last frame
    t_last = ts[-1]
    Z_last = 50.0 - 40.0*(t_last - 0.1)
    r_analytic = 100.0 / Z_last
    
    # Check within 1.0 px tolerance
    assert abs(radii[-1] - r_analytic) <= 1.0

def test_reproducibility(base_config, tmp_path):
    conf = base_config.copy()
    f1, t1 = generator.generate_stimulus(conf)
    f2, t2 = generator.generate_stimulus(conf)
    assert np.array_equal(f1, f2)
    assert np.array_equal(t1, t2)
    
    # Round-trip API test
    npz, jsn = stimulus_io.save_stimulus(tmp_path, conf, f1, t1)
    
    load_f, load_t, meta, load_c = loader.load_stimulus(tmp_path, conf["stimulus_id"])
    
    assert np.array_equal(f1, load_f)
    assert np.array_equal(t1, load_t)
    assert load_c["fps"] == conf["fps"]
    assert meta["n_frames"] == len(t1)

def test_seed_effect(base_config):
    # Seed doesn't affect deterministic geometric rendering. Documented.
    conf1 = base_config.copy()
    conf2 = base_config.copy()
    conf2["random_seed"] = 999
    
    f1, _ = generator.generate_stimulus(conf1)
    f2, _ = generator.generate_stimulus(conf2)
    assert np.array_equal(f1, f2)
