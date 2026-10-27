import numpy as np
import pytest
from dashboard.simulation.avoidance.perception import VisualTracker
from dashboard.simulation.avoidance.world import render_camera

def images(c,points):return render_camera(c,np.zeros(c.dimensions),np.array(points,dtype=float),[1.5]*len(points))[0]

def test_separate_objects_have_distinct_image_derived_tracks(settings):
    c=settings();tracker=VisualTracker(c);image=images(c,[[-5,20,0],[5,20,0]])
    first,_=tracker.observe(image,0);second,reasons=tracker.observe(image,1000/60)
    assert len(second)==2;assert len({t.identity for t in second})==2
    assert [t.identity for t in first]==[t.identity for t in second]
    assert all(t.motion_valid for t in second);assert not reasons

def test_merge_never_claims_valid_identity(settings):
    c=settings();tracker=VisualTracker(c);tracker.observe(images(c,[[-4,20,0],[4,20,0]]),0)
    tracks,reasons=tracker.observe(images(c,[[0,20,0]]),1000/60)
    assert 'lost_or_merged_track' in reasons
    assert not all(t.motion_valid for t in tracks)

def test_timestamp_gap_breaks_motion_and_no_object_is_unknown(settings):
    c=settings();tracker=VisualTracker(c);image=images(c,[[0,20,0]])
    tracker.observe(image,0);tracks,_=tracker.observe(image,100)
    assert not tracks[0].motion_valid
    empty,reasons=tracker.observe(np.full(image.shape,128,dtype=np.uint8),200)
    assert not empty and 'no_visible_object_depth_unknown' in reasons
    with pytest.raises(ValueError):tracker.current(199)

def test_tracking_accepts_no_world_ids_or_geometry(settings):
    import inspect
    assert list(inspect.signature(VisualTracker.observe).parameters)==['self','image','time_ms']
