import math
import numpy as np
import pytest
from dashboard.simulation.room_flight.pose import rotation,axis_angle,slerp,heading_step
from dashboard.simulation.room_flight.geometry import swept_sphere_box,ray_part
from dashboard.simulation.room_flight.world import RoomWorld

def test_body_rear_rotates_with_heading():
    r=rotation(axis_angle([0,0,1],math.pi/2))
    np.testing.assert_allclose(r@[0,1,0],[-1,0,0],atol=1e-12)
    np.testing.assert_allclose(r.T@(r@[1,2,3]),[1,2,3],atol=1e-12)

def test_quaternion_shortest_interpolation_and_heading_rate():
    q=axis_angle([0,0,1],1);np.testing.assert_allclose(slerp(q,-q,.5),q)
    changed=heading_step([0,0,0,1],[1,0,0],2,.001)
    assert 2*math.acos(changed[3])==pytest.approx(.002)

def test_exact_box_corner_rejects_inflated_box_false_contact():
    hit,clear=swept_sphere_box([1.9,1.9,-3],[0,0,6],[1,1,1],1)
    assert hit is None and clear>0

def test_box_face_swept_contact():
    hit,clear=swept_sphere_box([0,0,5],[0,0,-10],[1,1,1],.5)
    assert hit==pytest.approx(.35) and clear<0

def test_room_physics_and_sensor_use_same_box(config,solid,scene):
    c=config();s=solid(shape='box');part=s.parts[0]
    distance=ray_part(np.zeros(3),np.array([[0.,1.,0.]]),s.position(0),part)
    assert distance[0]==pytest.approx(8)
    hit,_=swept_sphere_box([0,-10,0],[0,20,0],[2,2,2],.5)
    assert hit==pytest.approx(.375)

def test_delayed_vertical_motor_and_room_orientation(config,scene):
    c=config();w=RoomWorld(c,scene());w.request([0,0,20])
    for _ in range(21):w.step()
    np.testing.assert_array_equal(w.fly,[0,0,0]);w.step();assert w.fly[2]==pytest.approx(.0004)

@pytest.mark.parametrize('axis,side',[(a,s) for a in range(3) for s in (-1,1)])
def test_all_room_faces_stop_at_fractional_swept_contact(config,scene,axis,side):
    from dataclasses import replace
    p=np.zeros(3);p[axis]=side*29.49;v=np.zeros(3);v[axis]=side*20
    w=RoomWorld(config(),replace(scene(velocity=tuple(v)),fly_position=tuple(p)))
    w.step()
    assert w.failure['kind']=='boundary' and w.time_ms==pytest.approx(.5)
    assert w.fly[axis]==pytest.approx(side*29.5)

def test_furniture_contact_cannot_be_crossed_between_saved_frames(config,solid,scene):
    from dataclasses import replace
    block=solid('furniture',(0,2.51,0),shape='box');block=replace(block,keyframes=block.keyframes[:1])
    w=RoomWorld(config(),scene(static=(block,),velocity=(0,20,0)))
    w.step()
    assert w.failure['object_id']=='furniture' and w.time_ms==pytest.approx(.5)
