import yaml
from pathlib import Path

def load_config(path: str | Path) -> dict:
    """Load and validate Phase 5 stimulus configuration."""
    with open(path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Validation
    req_fields = [
        "stimulus_id", "stimulus_type", "width", "height", "fps", 
        "duration_ms", "background_intensity", "object_intensity", 
        "initial_position", "initial_radius", "shape", 
        "start_time_ms", "random_seed"
    ]
    for field in req_fields:
        if field not in config:
            raise ValueError(f"Missing required config field: {field}")
            
    if config["shape"] != "circle":
        raise ValueError("Only 'circle' shape is supported.")
        
    if config["width"] <= 0 or config["height"] <= 0:
        raise ValueError("Dimensions must be positive.")
        
    if config["fps"] <= 0:
        raise ValueError("FPS must be positive.")
        
    if config["duration_ms"] <= 0:
        raise ValueError("Duration must be positive.")
        
    stype = config["stimulus_type"]
    valid_types = ["static", "translating", "looming", "control_static", "control_translating", "control_background"]
    if stype not in valid_types:
        raise ValueError(f"Invalid stimulus_type: {stype}")
        
    if stype == "looming":
        if "expansion_params" not in config:
            raise ValueError("Looming stimulus requires 'expansion_params'.")
        ep = config["expansion_params"]
        for p in ["f_R", "Z0", "v", "t_onset_ms"]:
            if p not in ep:
                raise ValueError(f"expansion_params missing {p}")
                
        # Validate Z > 0 condition
        Z0 = ep["Z0"]
        v = ep["v"]
        t_onset_s = ep["t_onset_ms"] / 1000.0
        dur_s = config["duration_ms"] / 1000.0
        Z_end = Z0 - v * (dur_s - t_onset_s)
        
        if Z_end <= 1.0: # Minimum margin of 1.0
            raise ValueError(f"Looming trajectory leads to Z={Z_end} <= 1.0 at final frame. Collision/negative distance invalid.")
            
    if stype in ["translating", "control_translating"]:
        for f in ["motion_direction_deg", "speed_px_per_s"]:
            if f not in config:
                raise ValueError(f"Translating stimulus requires {f}")
                
    return config
