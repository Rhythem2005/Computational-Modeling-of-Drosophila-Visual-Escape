"""Versioned abstract world definition and predeclared engineering fixtures."""
from copy import deepcopy
import numpy as np
import yaml
from connectome.scripts.phase5.config import validate_id
from connectome.scripts.phase7.evidence import ROOT

BASE = ROOT / "connectome/phase9"
OUT = BASE / "results"
FIELDS = {"version", "protocol_id", "duration_ms", "world_dt_ms", "world_units", "bounds_xy", "fly_radius",
          "camera_width", "camera_height", "camera_fps", "camera_center_px", "camera_focal_px", "camera_near_depth",
          "camera_orientation", "background_uint8", "object_uint8", "actuation_delay_ms", "escape_speed_max",
          "escape_acceleration_max", "escape_lateral_angle_max_deg", "success_final_clearance_min",
          "obstacle_motion_onset_ms", "spatial_seeds", "primary_condition", "secondary_condition", "calibration_scope"}


def validate_config(config):
    c = deepcopy(config)
    if set(c) != FIELDS:
        raise ValueError("World config fields differ from version 1.0")
    fixed = dict(version="1.0.0", protocol_id="fly_closed_loop_engineering_v1", world_dt_ms=1.0, world_units="abstract",
                 camera_width=256, camera_height=256, camera_fps=60, camera_orientation="stabilized_positive_world_y",
                 spatial_seeds=[55010,55011,55012,55013,55014], primary_condition="uniform_population",
                 secondary_condition="synthetic_fields_within_type_and_side_v1",
                 calibration_scope="frozen_open_loop_threshold_reused_without_world_calibration")
    if any(c[k] != v for k,v in fixed.items()):
        raise ValueError("Unsupported frozen scheduling/condition")
    for k in ("duration_ms", "actuation_delay_ms", "obstacle_motion_onset_ms"):
        if type(c[k]) is not int or c[k] < 0:
            raise ValueError(f"{k} must be nonnegative integer ms")
    if not 0 < c["duration_ms"] <= 1000 or not c["obstacle_motion_onset_ms"] < c["duration_ms"]:
        raise ValueError("Duration/onset outside supported world horizon")
    for k in ("fly_radius", "camera_focal_px", "camera_near_depth", "escape_speed_max", "escape_acceleration_max", "escape_lateral_angle_max_deg", "success_final_clearance_min"):
        if isinstance(c[k],bool) or not isinstance(c[k],(int,float)) or not np.isfinite(c[k]) or c[k] <= 0:
            raise ValueError(f"Invalid positive finite {k}")
    if c["escape_lateral_angle_max_deg"] > 90:
        raise ValueError("Escape angle must retain backward component")
    for k in ("background_uint8", "object_uint8"):
        if type(c[k]) is not int or not 0 <= c[k] <= 255:
            raise ValueError("Invalid pixel intensity")
    if c["background_uint8"] == c["object_uint8"]:
        raise ValueError("Object/background contrast is required")
    bounds = np.asarray(c["bounds_xy"],dtype=float)
    center = np.asarray(c["camera_center_px"],dtype=float)
    if bounds.shape != (2,2) or not np.all(np.isfinite(bounds)) or np.any(bounds[:,1]-bounds[:,0] <= 2*c["fly_radius"]):
        raise ValueError("Invalid world bounds")
    if center.shape != (2,) or not np.all(np.isfinite(center)) or not 0 <= center[0] < 256 or not 0 <= center[1] < 256:
        raise ValueError("Invalid camera center")
    return c


def load_config():
    return validate_config(yaml.safe_load((BASE / "environment_config.yaml").read_text()))


def validate_scenario(scenario):
    s = deepcopy(scenario)
    if set(s) != {"scenario_id", "fly_position", "obstacles"} or not s["obstacles"]:
        raise ValueError("Invalid scenario schema")
    validate_id(s["scenario_id"])
    pos = np.asarray(s["fly_position"],dtype=float)
    if pos.shape != (2,) or not np.all(np.isfinite(pos)):
        raise ValueError("Invalid initial fly position")
    identities = []
    for ob in s["obstacles"]:
        if set(ob) != {"id", "position", "velocity", "radius"}:
            raise ValueError("Invalid obstacle fields")
        validate_id(ob["id"]); identities.append(ob["id"])
        if isinstance(ob["radius"],bool) or not isinstance(ob["radius"],(int,float)) or not np.isfinite(ob["radius"]) or ob["radius"] <= 0:
            raise ValueError("Invalid obstacle radius")
        for k in ("position", "velocity"):
            a = np.asarray(ob[k],dtype=float)
            if a.shape != (2,) or not np.all(np.isfinite(a)):
                raise ValueError("Invalid obstacle geometry")
    if len(set(identities)) != len(identities):
        raise ValueError("Duplicate obstacle identities")
    return s


def fixtures():
    result = []
    for name,x in (("head_on",0.0),("left",-6.0),("right",6.0),("static",0.0),("near_miss",0.0)):
        v = [0.0,0.0] if name == "static" else ([6.25,-25.0] if name == "near_miss" else [-x/.8,-25.0])
        result.append(validate_scenario(dict(scenario_id=f"world_{name}", fly_position=[0.0,0.0],
                      obstacles=[dict(id="obstacle_0",position=[x,20.0],velocity=v,radius=1.5)])))
    return result
