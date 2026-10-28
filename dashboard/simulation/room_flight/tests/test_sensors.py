from dataclasses import replace
import numpy as np
import pytest
from dashboard.simulation.room_flight.sensors import SurroundRenderer
from dashboard.simulation.room_flight.pose import axis_angle
from dashboard.simulation.room_flight.perception import SurroundObserver

@pytest.mark.parametrize('index,position',[(0,(0,10,0)),(1,(0,-10,0)),(2,(-10,0,0)),(3,(10,0,0)),(4,(0,0,10)),(5,(0,0,-10))])
def test_true_six_axis_objects_have_visible_sensor_pixels(config,solid,scene,index,position):
    c=config();obs=SurroundRenderer(c).capture(scene((solid(position=position),)),np.zeros(3),np.array([0,0,0,1]),0)
    mask=np.all(obs.images[index]==[220,60,90],axis=-1)
    assert mask.any();assert obs.views[index].id==['front','rear','left','right','above','below'][index]

def test_body_rotation_changes_sensor_direction_not_spectator(config,solid,scene):
    c=config();s=scene((solid(position=(0,-10,0)),));renderer=SurroundRenderer(c)
    front=renderer.capture(s,np.zeros(3),axis_angle([0,0,1],np.pi),0)
    assert np.any(np.all(front.images[0]==[220,60,90],axis=-1))

def test_occluded_object_is_not_visible(config,solid,scene):
    c=config();block=replace(solid('wall',(0,5,0),shape='box',color=(40,50,45)),keyframes=({'time_ms':0,'position':(0,5,0)},))
    obs=SurroundRenderer(c).capture(scene((solid(position=(0,10,0)),),(block,)),np.zeros(3),[0,0,0,1],0)
    assert not np.any(np.all(obs.images[0]==[220,60,90],axis=-1))

def test_perception_receives_pixels_and_own_pose_without_scene_ids(config,solid,scene):
    c=config();renderer=SurroundRenderer(c);observer=SurroundObserver(c);s=scene((solid('secret_evaluator_id',position=(0,-10,0)),))
    observer.observe(renderer.capture(s,np.zeros(3),[0,0,0,1],0))
    tracks,_=observer.observe(renderer.capture(s,np.zeros(3),[0,0,0,1],1000/60))
    assert len(tracks)==1 and tracks[0]['motion_valid']
    assert isinstance(tracks[0]['id'],int) and tracks[0]['views']==['rear']
    assert not hasattr(renderer.capture(s,np.zeros(3),[0,0,0,1],0),'scene')

def test_camera_handoff_deduplicates_same_sphere(config,solid,scene):
    c=config();s=scene((solid(position=(15,15,0)),));observer=SurroundObserver(c);renderer=SurroundRenderer(c)
    tracks,_=observer.observe(renderer.capture(s,np.zeros(3),[0,0,0,1],0))
    assert len(tracks)==1
    assert len(tracks[0]['views'])>=2

def test_pure_body_rotation_preserves_static_object_world_velocity(config,solid,scene):
    c=config();s=scene((solid(position=(0,10,0)),));observer=SurroundObserver(c);renderer=SurroundRenderer(c)
    observer.observe(renderer.capture(s,np.zeros(3),[0,0,0,1],0))
    tracks,_=observer.observe(renderer.capture(s,np.zeros(3),axis_angle([0,0,1],np.pi),1000/60))
    assert len(tracks)==1 and tracks[0]['id']==0 and tracks[0]['motion_valid']
    np.testing.assert_allclose(tracks[0]['velocity'],0,atol=1e-10)
    assert tracks[0]['views']==['rear']

def test_focal_calibration_mismatch_is_rejected(config,solid,scene):
    c=config();obs=SurroundRenderer(c).capture(scene(),np.zeros(3),[0,0,0,1],0)
    obs=replace(obs,views=(replace(obs.views[0],focal_px=20),*obs.views[1:]))
    with pytest.raises(ValueError,match='calibration'):SurroundObserver(c).observe(obs)
