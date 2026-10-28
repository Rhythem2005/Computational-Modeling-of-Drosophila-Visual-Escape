"""Tiny deterministic software fixtures, not approved research settings or results."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from dataclasses import replace
import pytest
from dashboard.simulation.avoidance.contracts import Settings
from dashboard.simulation.room_flight.contracts import RoomConfig,Vision,Scene,Solid
from dashboard.simulation.room_flight.geometry import Part
from dashboard.simulation.room_flight.sensors import axis_rig

@pytest.fixture
def config():
    def make(**changes):
        m=Settings(dimensions=3,duration_ms=100,bounds=((-30,30),)*3,fly_radius=.5,object_radius_prior=1.5,camera_width=24,camera_height=24,camera_fps=60,camera_center_px=(12,12),camera_focal_px=10,camera_near_depth=.1,background_uint8=128,object_uint8=64,min_contrast_uint8=4,actuation_delay_ms=20,escape_speed_max=20,escape_acceleration_max=400,prediction_horizon_ms=100,candidate_directions=((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)),association_gate_px=10,association_ambiguity_px=1,max_radius_fraction_change=.5,max_shape_error_fraction=.5,clearance_margin=0,max_observation_age_ms=34,success_final_clearance_min=1)
        c=RoomConfig(m,axis_rig(24,24,10),Vision((220,60,90),5,1,.2,.5,.3,5,.1,34),(0,0,0),2,20,True,True,(35,45,40))
        return replace(c,**changes)
    return make

@pytest.fixture
def solid():
    def make(name='unit',position=(0,10,0),velocity=(0,0,0),shape='sphere',color=(220,60,90),end=100):
        part=Part(shape,(0,0,0),(0,0,0,1),color,radius=1.5 if shape=='sphere' else None,half_extents=(2,2,2) if shape=='box' else None)
        keys=({'time_ms':0,'position':position},{'time_ms':end,'position':tuple(position[i]+velocity[i]*end/1000 for i in range(3))})
        return Solid(name,(part,),keys)
    return make

@pytest.fixture
def scene():
    def make(dynamic=(),static=(),q=(0,0,0,1),velocity=(0,0,0)):
        return Scene('unit_contract',(0,0,0),velocity,q,static,dynamic,())
    return make
