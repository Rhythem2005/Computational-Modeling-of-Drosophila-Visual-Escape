import json
import numpy as np
from pathlib import Path

def load_stimulus(data_dir: str | Path, stimulus_id: str) -> tuple[np.ndarray, np.ndarray, dict, dict]:
    """
    Phase 6 API: Loader for visual stimulus.
    Returns: (frames, timestamps_s, metadata, config)
    
    frames: ndarray [T, H, W] uint8
    timestamps_s: ndarray [T] float
    metadata: dict
    config: dict
    """
    data_dir = Path(data_dir)
    npz_path = data_dir / f"{stimulus_id}.npz"
    json_path = data_dir / f"{stimulus_id}_metadata.json"
    
    if not npz_path.exists():
        raise FileNotFoundError(f"Missing frames file: {npz_path}")
    if not json_path.exists():
        raise FileNotFoundError(f"Missing metadata file: {json_path}")
        
    # Load arrays
    with np.load(npz_path) as data:
        frames = data["frames"]
        timestamps_s = data["timestamps_s"]
        
    # Load metadata
    with open(json_path, 'r') as f:
        metadata = json.load(f)
        
    config = metadata["config_snapshot"]
    
    return frames, timestamps_s, metadata, config
