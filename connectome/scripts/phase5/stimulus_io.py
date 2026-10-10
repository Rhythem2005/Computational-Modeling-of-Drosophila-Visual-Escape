import json
import hashlib
import numpy as np
from pathlib import Path
from datetime import datetime

def generate_metadata(config: dict, frames: np.ndarray, timestamps: np.ndarray) -> dict:
    """Generate strictly verifiable metadata for the saved stimulus."""
    config_json = json.dumps(config, sort_keys=True)
    config_hash = hashlib.sha256(config_json.encode('utf-8')).hexdigest()
    
    # Simple dependency versions
    import numpy as np
    
    deps = {
        "numpy": np.__version__,
    }
    
    metadata = {
        "stimulus_id": config["stimulus_id"],
        "stimulus_type": config["stimulus_type"],
        "dimensions": {"width": config["width"], "height": config["height"]},
        "fps": config["fps"],
        "n_frames": len(timestamps),
        "duration_s": config["duration_ms"] / 1000.0,
        "geometry": config["shape"],
        "intensities": {"background": config["background_intensity"], "object": config["object_intensity"]},
        "random_seed": config["random_seed"],
        "coordinate_convention": "origin top-left, +x right, +y down",
        "rendering_method": "hard-edged Euclidean distance threshold",
        "config_snapshot": config,
        "config_hash": config_hash,
        "library_versions": deps,
        "run_date": datetime.utcnow().isoformat() + "Z"
    }
    
    if config["stimulus_type"] in ["translating", "control_translating"]:
        metadata["motion_params"] = {
            "direction_deg": config["motion_direction_deg"],
            "speed_px_per_s": config["speed_px_per_s"]
        }
    if config["stimulus_type"] == "looming":
        metadata["expansion_params"] = config["expansion_params"]
        
    return metadata

def save_stimulus(out_dir: str | Path, config: dict, frames: np.ndarray, timestamps: np.ndarray):
    """Save stimulus data (frames as lossless .npz, metadata as .json)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    sid = config["stimulus_id"]
    npz_path = out_dir / f"{sid}.npz"
    json_path = out_dir / f"{sid}_metadata.json"
    
    # Save frames and timestamps (lossless compression)
    np.savez_compressed(npz_path, frames=frames, timestamps_s=timestamps)
    
    # Save metadata
    meta = generate_metadata(config, frames, timestamps)
    with open(json_path, 'w') as f:
        json.dump(meta, f, indent=2)
        
    return npz_path, json_path
