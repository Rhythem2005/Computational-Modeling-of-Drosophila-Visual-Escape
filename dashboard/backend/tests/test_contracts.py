"""Unexecuted until approval. Synthetic unit inputs are not displayed results."""
import sys
from pathlib import Path
import numpy as np
import pytest
from fastapi.testclient import TestClient
from fly_dashboard.config import Settings
from fly_dashboard.main import create_app
from fly_dashboard.repository import Repository, safe_json, png_gray
from fly_dashboard.live import LiveFrame

def test_no_execution_routes(tmp_path):
    app=create_app(Settings(tmp_path))
    with TestClient(app) as client:
        assert client.get('/api/v1/health').json()['experiment_execution'] is False
        assert client.post('/api/v1/simulations/start').status_code in (404,405)
        assert client.post('/api/v1/training/start').status_code in (404,405)
        assert client.get('/api/v1/catalog').json()['episodes']==[]

def test_unconfigured_producer_cannot_ingest(tmp_path):
    with TestClient(create_app(Settings(tmp_path))) as client:
        response=client.post('/api/v1/live',json=dict(name='unit',protocol='unit',controller='unit',source_note='test only',world_config={'fly_radius':.5}))
        assert response.status_code==403

def test_source_path_cannot_escape_results(tmp_path):
    settings=Settings(tmp_path)
    with pytest.raises(ValueError):settings.scientific_path('../private')
    with pytest.raises(ValueError):settings.scientific_path('/etc')

def test_opaque_episode_lookup_rejects_paths(tmp_path):
    repository=Repository(Settings(tmp_path))
    with pytest.raises(KeyError):repository.load('../../anything')

def test_nonfinite_missing_fields_are_json_null():
    assert safe_json(np.array([1.,np.nan,np.inf]))==[1.,None,None]

def test_png_is_grayscale_and_dimensioned():
    import struct
    result=png_gray(np.full((3,4),128,dtype=np.uint8))
    assert result[:8]==b'\x89PNG\r\n\x1a\n'
    assert struct.unpack('!II',result[16:24])==(4,3)

def test_future_camera_telemetry_is_rejected():
    with pytest.raises(ValueError):LiveFrame(time_ms=1,fly=[0,0],obstacles=[],camera_timestamp_ms=2)

def test_state_identity_width_is_explicit():
    with pytest.raises(ValueError):LiveFrame(time_ms=1,fly=[0,0],obstacles=[],neural_kind='anatomical',neural_ids=['H0'],neural_values=[.2])

def test_three_dimensional_telemetry_preserves_altitude():
    value=LiveFrame(time_ms=10,fly=[1,2,3],obstacles=[dict(id='unit',position=[4,5,6],radius=1)],decision_timestamp_ms=9,neural_timestamp_ms=10)
    assert value.fly[2]==3
    with pytest.raises(ValueError):LiveFrame(time_ms=10,fly=[1,2,3],obstacles=[dict(id='unit',position=[4,5],radius=1)])
    with pytest.raises(ValueError):LiveFrame(time_ms=10,fly=[1,2,3],obstacles=[],decision_timestamp_ms=11)

def test_new_3d_recording_can_be_loaded_without_starting_science(tmp_path):
    import json,hashlib
    root=tmp_path/'dashboard/runs/unit/episodes';root.mkdir(parents=True)
    payload=root/'unit.npz'
    np.savez_compressed(payload,schema_version=np.array('multi_object_1.0'),frame_valid=np.array([True]),frame_frozen_domain_valid=np.array([False]),world_times_ms=np.array([0.,1.]),fly_position=np.zeros((2,3)),obstacle_positions=np.array([[[0.,10.,3.]],[[0.,10.,3.]]]),decision_times_ms=np.array([0.]),frames=np.full((1,2,2),128,dtype=np.uint8),frame_timestamps_s=np.array([0.]),controller_states=np.empty((2,0)),controller_state_times_ms=np.array([0.,1.]),body_ids=np.array([],dtype=int))
    meta=dict(arrays_sha256=hashlib.sha256(payload.read_bytes()).hexdigest(),config=dict(world_dimension=3,fly_radius=.5,duration_ms=1),scenario=dict(scenario_id='unit',fly_position=[0,0,0],obstacles=[dict(id='unit',position=[0,10,3],velocity=[0,0,0],radius=1)]),metrics=dict(end_ms=1),model='unit')
    payload.with_suffix('.json').write_text(json.dumps(meta))
    repo=Repository(Settings(tmp_path));catalog=repo.refresh();assert catalog['source_count']==1
    replay=repo.load(catalog['episodes'][0]['id'])['payload']
    assert replay['world']['obstacles'][0][0][2]==3
    assert replay['neural']['kind']=='unavailable'
    assert replay['encoder']['valid']==[False]

def test_authenticated_3d_producer_to_viewer_roundtrip(tmp_path):
    headers={'X-Fly-Ingest-Token':'unit-only-token'}
    with TestClient(create_app(Settings(tmp_path,ingest_token='unit-only-token'))) as client:
        health=client.get('/api/v1/health').json()
        assert health['world_dimensions']==[2,3] and health['separate_signal_timestamps']
        created=client.post('/api/v1/live',headers=headers,json=dict(name='Synthetic contract check',protocol='unit_only',controller='unit',source_note='Test inputs; not scientific results',world_config=dict(fly_radius=.5,world_dimension=3)))
        assert created.status_code==200
        ident=created.json()['id']
        frame=dict(time_ms=10,decision_timestamp_ms=9,neural_timestamp_ms=10,fly=[1,2,3],obstacles=[dict(id='left',position=[-3,8,4],radius=1),dict(id='right',position=[3,8,-4],radius=1)])
        assert client.post(f'/api/v1/live/{ident}/frames',json=frame).status_code==403
        with client.websocket_connect(f'/api/v1/live/{ident}/ws') as ws:
            assert ws.receive_json()['type']=='snapshot'
            assert client.post(f'/api/v1/live/{ident}/frames',headers=headers,json=frame).status_code==200
            received=ws.receive_json()['frame']
            assert received['fly']==[1,2,3] and len(received['obstacles'])==2
            assert received['decision_timestamp_ms']==9
            bad=dict(frame,time_ms=11,fly=[1,2],obstacles=[])
            assert client.post(f'/api/v1/live/{ident}/frames',headers=headers,json=bad).status_code==409
            assert client.post(f'/api/v1/live/{ident}/end',headers=headers,json={}).status_code==200
            assert ws.receive_json()['type']=='ended'

def test_room_rgb_pose_and_surround_schema():
    import base64
    from fly_dashboard.live import LiveSpec
    png=png_gray(np.full((4,4,3),[50,80,100],dtype=np.uint8))
    assert png[25]==2  # PNG truecolor; old grayscale remains color type 0.
    frame=LiveFrame(time_ms=10,fly=[0,0,0],fly_quaternion_xyzw=[0,0,0,1],obstacles=[],sensor_views=[dict(id='rear',time_ms=9,quaternion_xyzw=[0,0,1,0],png_base64=base64.b64encode(png).decode())])
    assert frame.sensor_views[0].id=='rear'
    with pytest.raises(ValueError):LiveFrame(time_ms=10,fly=[0,0,0],fly_quaternion_xyzw=[0,0,0,2],obstacles=[])
    with pytest.raises(ValueError):LiveFrame(time_ms=10,fly=[0,0,0],obstacles=[],sensor_views=[dict(id='rear',time_ms=11,quaternion_xyzw=[0,0,1,0],png_base64=base64.b64encode(png).decode())])

def test_rgb_room_replay_preserves_body_orientation_and_camera_rig(tmp_path):
    import json,hashlib
    folder=tmp_path/'dashboard/runs/room_unit/episodes';folder.mkdir(parents=True);p=folder/'room.npz'
    q=np.array([[0.,0.,0.,1.],[0.,0.,0.,1.]])
    np.savez_compressed(p,schema_version=np.array('room_flight_1.0'),world_times_ms=np.array([0.,1.]),fly_position=np.zeros((2,3)),fly_quaternion_xyzw=q,obstacle_positions=np.empty((2,0,3)),decision_times_ms=np.array([0.]),frames=np.zeros((1,8,12,3),dtype=np.uint8),frame_timestamps_s=np.array([0.]),controller_states=np.empty((2,0)),controller_state_times_ms=np.array([0.,1.]),body_ids=np.array([],dtype=int))
    p.with_suffix('.json').write_text(json.dumps(dict(arrays_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),config=dict(world_dimension=3,room_flight=True,fly_radius=.5,duration_ms=1,camera_rig=[dict(id='front')]),scenario=dict(scenario_id='unit',fly_position=[0,0,0],obstacles=[]),metrics=dict(end_ms=1),model='unit')))
    repo=Repository(Settings(tmp_path));rows=repo.refresh()['episodes'];loaded=repo.load(rows[0]['id'])
    assert loaded['payload']['world']['quaternion_xyzw'][0]==[0,0,0,1]
    assert loaded['payload']['camera']['view_ids']==['front']
    assert loaded['camera_png'][25]==2

def test_producer_preflight_validates_auth_without_creating_a_session(tmp_path):
    with TestClient(create_app(Settings(tmp_path,ingest_token='unit-only'))) as client:
        spec=dict(name='unit',protocol='unit',controller='unit',source_note='test only',world_config=dict(fly_radius=.5,world_dimension=3))
        assert client.post('/api/v1/producer/check',json=spec).status_code==403
        result=client.post('/api/v1/producer/check',headers={'X-Fly-Ingest-Token':'unit-only'},json=spec).json()
        assert result['authenticated'] and result['available_sessions']==4 and not result['creates_session']
        health=client.get('/api/v1/health').json()
        assert health['surround_rgb'] and health['body_orientation'] and health['telemetry_schema']=='live_telemetry_1.2'
        assert client.get('/api/v1/live').json()['sessions']==[]

def test_room_transport_requires_pose_calibration_and_synchronized_rgb(tmp_path):
    import base64
    headers={'X-Fly-Ingest-Token':'unit-only'}
    view=dict(id='front',quaternion=[0,0,0,1],width=4,height=4,focal_px=2)
    image=dict(id='front',time_ms=0,quaternion_xyzw=view['quaternion'],png_base64=base64.b64encode(png_gray(np.zeros((4,4,3),dtype=np.uint8))).decode())
    spec=dict(name='unit',protocol='unit',controller='unit',source_note='Software contract only',world_config=dict(fly_radius=.5,world_dimension=3,room_flight=True,camera_rig=[view]))
    with TestClient(create_app(Settings(tmp_path,ingest_token='unit-only'))) as client:
        ident=client.post('/api/v1/live',headers=headers,json=spec).json()['id']
        frame=dict(time_ms=0,fly=[0,0,0],obstacles=[],camera_timestamp_ms=0,sensor_views=[image])
        assert client.post(f'/api/v1/live/{ident}/frames',headers=headers,json=frame).status_code==409
        frame['fly_quaternion_xyzw']=[0,0,0,1]
        bad=dict(frame,sensor_views=[dict(image,time_ms=.1)],time_ms=1)
        assert client.post(f'/api/v1/live/{ident}/frames',headers=headers,json=bad).status_code==409
        assert client.post(f'/api/v1/live/{ident}/frames',headers=headers,json=frame).status_code==200

def test_dashboard_html_is_not_cached_between_ui_updates(tmp_path):
    built=tmp_path/'dashboard/frontend/dist';built.mkdir(parents=True)
    (built/'index.html').write_text('<html>Current dashboard</html>')
    with TestClient(create_app(Settings(tmp_path))) as client:
        response=client.get('/')
        assert response.status_code==200
        assert response.headers['cache-control']=='no-store'
