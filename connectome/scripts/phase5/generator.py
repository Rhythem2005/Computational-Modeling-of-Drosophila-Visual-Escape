import numpy as np

def render_frame(width: int, height: int, bg_intensity: int, 
                 obj_intensity: int, cx: float, cy: float, r: float) -> np.ndarray:
    """
    Render a single grayscale frame.
    Coordinate system: (0,0) top-left, +x right, +y down.
    Rasterization: hard-edged Euclidean distance threshold.
    """
    frame = np.full((height, width), bg_intensity, dtype=np.uint8)
    if r <= 0:
        return frame
        
    Y, X = np.ogrid[:height, :width]
    dist_sq = (X - cx)**2 + (Y - cy)**2
    mask = dist_sq <= r**2
    frame[mask] = obj_intensity
    
    return frame

def compute_timestamps(duration_ms: float, fps: float) -> np.ndarray:
    """
    Compute timestamps for frames.
    Frames are positioned at i / fps.
    """
    duration_s = duration_ms / 1000.0
    n_frames = int(np.floor(duration_s * fps))
    return np.arange(n_frames) / fps

def generate_stimulus(config: dict) -> tuple[np.ndarray, np.ndarray]:
    """Generate frames and timestamps from config."""
    timestamps = compute_timestamps(config["duration_ms"], config["fps"])
    n_frames = len(timestamps)
    
    W = config["width"]
    H = config["height"]
    bg = config["background_intensity"]
    obj = config["object_intensity"]
    cx, cy = config["initial_position"]
    r0 = config["initial_radius"]
    stype = config["stimulus_type"]
    
    frames = np.empty((n_frames, H, W), dtype=np.uint8)
    
    if stype == "control_background":
        # Background only, no object
        r0 = 0.0
        
    for i, t in enumerate(timestamps):
        curr_cx, curr_cy, curr_r = cx, cy, r0
        
        # Apply start time logic (if before start_time_ms, object might not exist or starts moving)
        # But for simplicity, we assume the object exists. We apply motion/expansion after start time/onset.
        if stype in ["translating", "control_translating"]:
            if t >= config["start_time_ms"] / 1000.0:
                dt = t - config["start_time_ms"] / 1000.0
                theta = np.radians(config["motion_direction_deg"])
                speed = config["speed_px_per_s"]
                curr_cx += np.cos(theta) * speed * dt
                curr_cy -= np.sin(theta) * speed * dt # -sin because +y is down
                
        if stype == "looming":
            ep = config["expansion_params"]
            t_onset = ep["t_onset_ms"] / 1000.0
            if t > t_onset:
                Z_t = ep["Z0"] - ep["v"] * (t - t_onset)
                # Geometric model: r(t) = f*R / Z(t)
                curr_r = ep["f_R"] / Z_t
            else:
                curr_r = ep["f_R"] / ep["Z0"]
                
        # Clipping: if the object exceeds the frame entirely, it gets naturally clipped by the mask.
        frames[i] = render_frame(W, H, bg, obj, curr_cx, curr_cy, curr_r)
        
    return frames, timestamps
