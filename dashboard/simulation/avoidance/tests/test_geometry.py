import numpy as np
import pytest
from dashboard.simulation.avoidance.world import swept_contact,World,render_camera
from dashboard.simulation.avoidance.contracts import Scenario

def test_swept_sphere_contact_between_endpoints():
    hit,clear=swept_contact(np.array([0.,0.,5.]),np.array([0.,0.,-10.]),1.)
    assert hit==pytest.approx(.4);assert clear==pytest.approx(-1.)

def test_tangency_is_contact_and_vertical_miss_is_not():
    assert swept_contact([1,0,5],[0,0,-10],1)[0]==pytest.approx(.5)
    assert swept_contact([0,2,5],[0,0,-10],1)[0] is None

def test_camera_projects_vertical_coordinates(settings):
    c=settings();fly=np.zeros(3)
    upper,_=render_camera(c,fly,np.array([[0,20,3]]),[1.5]);lower,_=render_camera(c,fly,np.array([[0,20,-3]]),[1.5])
    assert np.nonzero(upper!=128)[0].mean()<32<np.nonzero(lower!=128)[0].mean()

def test_two_dimensional_embedding_preserves_camera(settings):
    a,_=render_camera(settings(2),np.zeros(2),np.array([[2,20]]),[1.5])
    b,_=render_camera(settings(3),np.zeros(3),np.array([[2,20,0]]),[1.5])
    np.testing.assert_array_equal(a,b)

def test_delay_and_speed_bound_are_physical(settings):
    c=settings();s=Scenario('unit_delay',(0,0,0),(0,0,0),({'id':'unit','position':[20,20,20],'velocity':[0,0,0],'radius':1.5,'onset_ms':0},))
    w=World(c,s);w.request([0,0,20])
    for _ in range(21):w.step()
    np.testing.assert_array_equal(w.fly,[0,0,0])
    w.step();assert w.fly[2]==pytest.approx(.0004)
    for _ in range(100):w.step()
    assert np.linalg.norm(w.velocity)<=20;assert w.fly[2]>0

def test_initial_velocity_is_a_proprioceptive_state(settings):
    c=settings();s=Scenario('unit_coast',(0,0,0),(1,0,0),({'id':'unit','position':[20,20,20],'velocity':[0,0,0],'radius':1.5,'onset_ms':0},))
    w=World(c,s);w.step();assert w.fly[0]==pytest.approx(.001)
