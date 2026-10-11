from copy import deepcopy
import inspect
import json
import numpy as np
import pytest
from connectome.scripts.phase5.generator import generate_stimulus, render_frame
from connectome.scripts.phase5.stimulus_io import save_stimulus
from connectome.scripts.phase6.encoder import (
    CausalEncoder, extract_features, load_config, load_mapping,
    digest, fit_normalization, causal_hold, validate_config,
)
from connectome.scripts.phase6.dataset import movie_hash,check_isolation,encode_saved


def scene(kind="looming",polarity=1,contrast=64):
    c = dict(stimulus_id="fixture",stimulus_type=kind,width=128,height=128,
        fps=60,duration_ms=1000,initial_position=[64,64],initial_radius=10,
        background_intensity=128,object_intensity=128+polarity*contrast,
        shape="circle",start_time_ms=200,random_seed=1)
    if kind == "looming":
        c["expansion_params"] = dict(f_R=500,Z0=50,v=25,t_onset_ms=200,min_distance=1)
    if kind == "translating": c.update(speed_px_per_s=20,motion_direction_deg=0)
    return c


@pytest.fixture(scope="module")
def encoder():
    c = load_config()
    return CausalEncoder(c,dict(encoder_version="1.0.0",schema_version="1.0",config_sha256=digest(c),scales=[10,20]))


@pytest.mark.parametrize("kind",["static","translating","looming"])
@pytest.mark.parametrize("polarity",[-1,1])
@pytest.mark.parametrize("contrast",[12,64])
def test_controls_polarities_and_low_contrast(encoder,kind,polarity,contrast):
    frames,ts = generate_stimulus(scene(kind,polarity,contrast))
    out = encoder.encode(frames,ts)
    assert out.drive.shape == (60,321) and out.drive.dtype == np.float64
    assert np.all(np.isfinite(out.drive)) and np.min(out.drive) >= 0 and np.max(out.drive) <= 1
    assert np.all(out.channels[ts <= .2] == 0)
    if kind == "looming": assert np.all(out.channels.max(axis=0) > 0)
    else: assert np.all(out.channels == 0)


def test_static_final_size(encoder):
    frames,ts = generate_stimulus(scene())
    static = np.repeat(frames[-1:],len(ts),axis=0)
    assert np.all(encoder.encode(static,ts).drive == 0)


def test_polarity_exact(encoder):
    a,t = generate_stimulus(scene(polarity=1))
    b,_ = generate_stimulus(scene(polarity=-1))
    np.testing.assert_array_equal(encoder.encode(a,t).drive,encoder.encode(b,t).drive)


def test_zero_contrast(encoder):
    frames,t = generate_stimulus(scene(contrast=0))
    assert np.all(encoder.encode(frames,t).drive == 0)


def test_body_ids_and_uniform_broadcast(encoder):
    frames,t = generate_stimulus(scene())
    out = encoder.encode(frames,t)
    mapping = load_mapping()
    np.testing.assert_array_equal(out.body_ids,mapping["body_ids"])
    for ch in (0,1):
        indices = np.array(mapping["channel_index"]) == ch
        np.testing.assert_array_equal(out.drive[:,indices],np.repeat(out.channels[:,ch:ch+1],indices.sum(),axis=1))
    dn = np.array(mapping["channel_index"]) < 0
    assert dn.sum() == 10 and np.all(out.drive[:,dn] == 0)


@pytest.mark.parametrize("cut",[1,13,25,50])
def test_prefix_causality(encoder,cut):
    frames,t = generate_stimulus(scene())
    a = encoder.encode(frames,t)
    changed = frames.copy()
    changed[cut:] = 0
    b = encoder.encode(changed,t)
    prefix = encoder.encode(frames[:cut],t[:cut])
    np.testing.assert_array_equal(a.drive[:cut],b.drive[:cut])
    np.testing.assert_array_equal(a.drive[:cut],prefix.drive)


def test_reproducible(encoder):
    frames,t = generate_stimulus(scene())
    np.testing.assert_array_equal(encoder.encode(frames,t).drive,encoder.encode(frames,t).drive)


def test_metadata_boundary(encoder,tmp_path):
    c = scene()
    frames,t = generate_stimulus(c)
    save_stimulus(tmp_path,c,frames,t)
    meta_path = tmp_path/"fixture_metadata.json"
    a = encode_saved(encoder,tmp_path,"fixture")
    meta = json.loads(meta_path.read_text())
    meta["evaluator"] = dict(label=0,type="static",radius=1,speed=1)
    meta_path.write_text(json.dumps(meta))
    b = encode_saved(encoder,tmp_path,"fixture")
    meta["evaluator"] = dict(label=1,type="looming",radius=1e6,speed=1e6)
    meta_path.write_text(json.dumps(meta))
    other = encode_saved(encoder,tmp_path,"fixture")
    np.testing.assert_array_equal(a.drive,b.drive)
    np.testing.assert_array_equal(a.drive,other.drive)
    # Mandatory Phase 5 geometry fields cannot be corrupted through its loader;
    # evaluator dictionaries at this boundary are ignored, not trusted features.
    for metadata in (dict(label=0),dict(label=1,type="looming",radius=100,speed=200)):
        with pytest.raises(TypeError): encoder.encode(frames,t,metadata=metadata)
    assert list(inspect.signature(encoder.encode).parameters) == ["frames","timestamps_s"]


def test_fractional_and_ms_availability(encoder):
    f,_ = generate_stimulus(scene())
    t = np.arange(len(f),dtype=np.float64)/59.7 + .0037
    out = encoder.encode(f,t)
    assert np.all(np.isfinite(out.drive))
    # Exactly representable fixtures prevent decimal conversion artifacts.
    stamps = np.array([0.,.125,.25],dtype=np.float64)
    values = np.array([[0.,0.],[1.,2.],[3.,4.]])
    q = np.array([-.125,0.,.124,.125,.249,.25,.5],dtype=np.float64)
    expected = np.array([[0,0],[0,0],[0,0],[1,2],[1,2],[3,4],[3,4]])
    np.testing.assert_array_equal(causal_hold(values,stamps,q),expected)
    np.testing.assert_array_equal(causal_hold(values,stamps,(q*1000)/1000),expected)
    before = np.nextafter(stamps[1:],-np.inf)
    np.testing.assert_array_equal(causal_hold(values,stamps,before),values[:-1])


@pytest.mark.parametrize("case",["border","offscreen","fullfield"])
def test_clipping(encoder,case):
    frames = []
    for radius in np.linspace(10,30,60):
        cx = 0 if case == "border" else -100 if case == "offscreen" else 32
        frames.append(render_frame(64,64,128,200,cx,32,200 if case=="fullfield" else radius))
    f = np.stack(frames)
    t = np.arange(60,dtype=np.float64)/60
    out = encoder.encode(f,t)
    assert not out.diagnostics["valid"].any()
    assert np.all(out.drive == 0)


def test_contraction(encoder):
    f,t = generate_stimulus(scene())
    assert np.all(encoder.encode(f[::-1].copy(),t).drive == 0)


@pytest.mark.parametrize("case",["dtype","layout","empty","time_dtype","length","negative","nan","duplicate","reverse"])
def test_invalid_arrays(encoder,case):
    f,t = generate_stimulus(scene())
    if case == "dtype": f = f.astype(float)
    elif case == "layout": f = f[0]
    elif case == "empty": f,t = f[:0],t[:0]
    elif case == "time_dtype": t = t.astype(np.float32)
    elif case == "length": t = t[:-1]
    elif case == "negative": t[0] = -1
    elif case == "nan": t[0] = np.nan
    elif case == "duplicate": t[1] = t[0]
    elif case == "reverse": t = t[::-1].copy()
    with pytest.raises(ValueError): encoder.encode(f,t)


@pytest.mark.parametrize("key,value",[("growth_window_s",0),("min_area_growth_px",-1),("min_relative_radius_growth",float("nan")),("normalization_quantile",1.1),("min_contrast_uint8",False),("mapping","spatial"),("encoder_version","2.0")])
def test_invalid_config(key,value):
    c = load_config(); c[key] = value
    with pytest.raises(ValueError): validate_config(c)


def test_one_frame(encoder):
    f,t = generate_stimulus(scene())
    assert np.all(encoder.encode(f[:1],t[:1]).drive == 0)


def test_training_normalization():
    c = load_config()
    features = [np.array([[0.,0.],[1.,2.],[3.,4.]])]
    records = [dict(split="train",scenario_id="x",movie_sha256="hash")]
    norm = fit_normalization(features,c,records)
    np.testing.assert_allclose(norm["scales"],[2.99,3.99])
    records[0]["split"] = "test"
    with pytest.raises(ValueError,match="training"): fit_normalization(features,c,records)
    with pytest.raises(ValueError): fit_normalization([np.zeros((3,2))],c,[dict(split="train")])


@pytest.mark.parametrize("bad",["version","scales","mapping"])
def test_reject_bad_state(encoder,bad):
    norm = deepcopy(encoder.normalization)
    mapping = load_mapping()
    if bad == "version": norm["encoder_version"] = "2"
    if bad == "scales": norm["scales"] = [0,1]
    if bad == "mapping": mapping["channel_index"][0] = 0
    with pytest.raises(ValueError): CausalEncoder(load_config(),norm,mapping)


def test_movie_hash_shape_and_content():
    f = np.zeros((2,4,8),dtype=np.uint8)
    assert movie_hash(f) != movie_hash(f.reshape(2,8,4))
    other = f.copy(); other[0,0,0] = 1
    assert movie_hash(f) != movie_hash(other)


@pytest.mark.parametrize("case",["duplicate","family","id"])
def test_isolation_rejects_collisions(case):
    a = dict(scenario_id="a",group_id="g",split="train",cohort="train",movie_sha256="a")
    b = dict(scenario_id="b",group_id="h",split="test",cohort="test_id",movie_sha256="b")
    if case == "duplicate": b["movie_sha256"] = "a"
    if case == "family": b["group_id"] = "g"
    if case == "id": b["scenario_id"] = "a"
    with pytest.raises(ValueError): check_isolation([a,b])
