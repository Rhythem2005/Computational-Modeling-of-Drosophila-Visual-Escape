"""Deterministic algorithm fixtures only; these values are NOT research protocols."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
import pytest
from dashboard.simulation.avoidance.contracts import Settings,Scenario

@pytest.fixture
def settings():
    def make(dim=3,**overrides):
        data=dict(dimensions=dim,duration_ms=1000,bounds=tuple([(-50.,50.)]*dim),fly_radius=.5,object_radius_prior=1.5,
            camera_width=64,camera_height=64,camera_fps=60,camera_center_px=(32.,32.),camera_focal_px=40.,camera_near_depth=.1,
            background_uint8=128,object_uint8=64,min_contrast_uint8=10,actuation_delay_ms=20,escape_speed_max=20.,escape_acceleration_max=400.,
            prediction_horizon_ms=100,candidate_directions=tuple(tuple(1. if i==j else 0. for i in range(dim)) for j in range(dim))+tuple(tuple(-1. if i==j else 0. for i in range(dim)) for j in range(dim)),association_gate_px=10.,association_ambiguity_px=1.,max_radius_fraction_change=.5,max_shape_error_fraction=.5,clearance_margin=0.,max_observation_age_ms=34,success_final_clearance_min=1.)
        data.update(overrides);return Settings(**data)
    return make
