"""Synthetic unit images only, not behavioral evaluation conditions."""
import inspect
import numpy as np
import pytest
from connectome.scripts.collision_threat_v1.features import Camera,FeatureExtractor,extract,available_tick
from connectome.scripts.collision_threat_v1.common import require_stage_b_review

@pytest.fixture
def camera():return Camera(256,256,128.,128.,160.,60.,128,4)

def image(cx=128,cy=128,r=10):
    y,x=np.ogrid[:256,:256]
    a=np.full((256,256),128,dtype=np.uint8)
    a[(x-cx)**2+(y-cy)**2<=r*r]=64
    return a

def test_geometry_and_units(camera):
    row=FeatureExtractor(camera).update(image(144),0.)
    assert row['centroid_x_px']==144 and row['centroid_y_px']==128
    assert row['normalized_x']==.1
    assert row['bearing_rad']==float(np.arctan(.1))
    assert row['radius_px']==float(np.sqrt(row['area_px']/np.pi))
    assert row['half_extent_rad']==float(np.arctan(row['radius_px']/160))
    assert row['measurement_valid'] and not row['motion_valid']
    assert row['bearing_rate_rad_s'] is None

def test_adjacent_frame_derivatives(camera):
    e=FeatureExtractor(camera);a=e.update(image(),0.);b=e.update(image(129,r=11),1/60)
    assert b['motion_valid']
    assert b['centroid_x_rate_px_s']==60.
    assert b['extent_rate_rad_s']==(b['half_extent_rad']-a['half_extent_rad'])/(1/60)
    assert b['radius_rate_px_s']>0 and b['bearing_rate_rad_s']>0

def test_stationary_derivatives_are_defined_zero(camera):
    e=FeatureExtractor(camera);e.update(image(),0.);b=e.update(image(),1/60)
    assert b['motion_valid'] and b['radius_rate_px_s']==b['bearing_rate_rad_s']==0.

@pytest.mark.parametrize('kind',['empty','multiple','border','dominant'])
def test_invalid_views_are_unknown(camera,kind):
    if kind=='empty':a=np.full((256,256),128,dtype=np.uint8)
    elif kind=='multiple':a=np.minimum(image(80),image(176))
    elif kind=='border':a=image(1)
    else:a=np.full((256,256),64,dtype=np.uint8)
    e=FeatureExtractor(camera);e.update(image(),0.);row=e.update(a,1/60)
    assert not row['measurement_valid'] and not row['motion_valid'] and row['reasons']
    assert row['radius_px'] is None and row['bearing_rate_rad_s'] is None

def test_recovery_does_not_bridge_invalid_frame(camera):
    e=FeatureExtractor(camera);e.update(image(1),0.)
    assert not e.update(image(),1/60)['motion_valid']
    assert e.update(image(),2/60)['motion_valid']

def test_gap_breaks_derivatives_then_recovers(camera):
    e=FeatureExtractor(camera);e.update(image(),0.)
    gap=e.update(image(130),2/60)
    assert gap['timestamp_gap'] and not gap['motion_valid']
    assert e.update(image(131),3/60)['motion_valid']

def test_nominal_fractional_clock_is_not_a_gap(camera):
    e=FeatureExtractor(camera)
    for k in range(60):
        row=e.update(image(),k/60)
        assert not row['timestamp_gap']

@pytest.mark.parametrize('timestamp',[0.,-1.,float('nan'),float('inf'),True])
def test_invalid_clock_raises(camera,timestamp):
    e=FeatureExtractor(camera);e.update(image(),0.)
    with pytest.raises(ValueError):e.update(image(),timestamp)

@pytest.mark.parametrize('bad',[np.zeros((256,256),dtype=np.float64),np.zeros((2,2),dtype=np.uint8)])
def test_invalid_image_raises(camera,bad):
    with pytest.raises(ValueError):FeatureExtractor(camera).update(bad,0.)

def test_prefix_invariance_and_reset(camera):
    frames=np.stack([image(128+k) for k in range(6)]);times=np.arange(6,dtype=np.float64)/60
    original=extract(frames,times,camera);changed=frames.copy();changed[3:]=128
    assert extract(changed,times,camera)[:3]==original[:3]
    e=FeatureExtractor(camera);e.update(image(150),0.);e.reset()
    assert e.update(frames[0],times[0])==original[0]

def test_caller_mutation_does_not_change_history(camera):
    e=FeatureExtractor(camera);frame=image();row=e.update(frame,0.)
    frame[:]=0;row['radius_px']=999;row['measurement_valid']=False
    next_row=e.update(image(),1/60)
    assert next_row['motion_valid'] and next_row['radius_rate_px_s']==0

def test_no_evaluator_inputs_in_api():
    assert list(inspect.signature(FeatureExtractor.update).parameters)==['self','frame','timestamp_s']

def test_causal_tick_and_endpoint():
    assert available_tick(1/60)==17
    for n in range(60):
        ts=n/60;k=available_tick(ts)
        assert ts<=k/1000
        assert k==0 or ts>(k-1)/1000

def test_missing_rule_spec_blocks_prototype():
    with pytest.raises(ValueError,match='Stage B disabled'):require_stage_b_review(None)

def test_camera_contract_rejects_invalid():
    with pytest.raises(ValueError):Camera(256,256,128,128,0,60,128,4)
