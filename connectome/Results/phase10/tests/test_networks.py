import numpy as np
import pytest
from connectome.scripts.phase10.networks import population_average,weight_shuffle,rewire,invariants,stability,seed_schedule


def fixture():
    rng=np.random.default_rng(101)
    w=rng.integers(1,30,(10,10)).astype(np.float64)/172
    w[rng.random((10,10))<.7]=0;np.fill_diagonal(w,0)
    return w,[('A','left')]*5+[('A','right')]*5


def test_population_average_all_eligible_pairs_and_diagonal():
    w,g=fixture();m=population_average(w,g);r=invariants(w,m,g,'population_average')
    assert r['same_block_totals'] and not np.diag(m).any()
    assert m[:5,:5].sum()==pytest.approx(w[:5,:5].sum())
    assert m[0,1]==pytest.approx(w[:5,:5].sum()/20)
    assert (m>0).sum()>(w>0).sum()


@pytest.mark.parametrize('index',range(30))
def test_all_declared_weight_seeds_reproduce_block_constraints(index):
    w,g=fixture();seed=seed_schedule()['weight_shuffle'][index]
    a=weight_shuffle(w,g,seed);b=weight_shuffle(w,g,seed)
    np.testing.assert_array_equal(a,b)
    r=invariants(w,a,g,'weight_shuffle');assert r['same_topology'] and r['same_in_out_degrees'] and r['same_block_weight_multisets']


@pytest.mark.parametrize('index',range(30))
def test_all_declared_rewire_seeds_degrees_loops_duplicates_and_reproduction(index):
    _,g=fixture();w=np.zeros((10,10),dtype=np.float64)
    # Each of the four blocks starts with a permutation graph with known swaps.
    # Arbitrary sparse graphs can have degree-constrained rigid realizations.
    for post in range(10):
        for source_group in (0,5):
            pre=source_group+(post%5+(1 if post//5==source_group//5 else 0))%5
            w[post,pre]=(post+source_group+1)/172
    seed=seed_schedule()['degree_rewire'][index]
    a,r=rewire(w,g,seed);b,s=rewire(w,g,seed)
    np.testing.assert_array_equal(a,b);assert r==s and r['status']=='PASS'
    assert all(v for k,v in invariants(w,a,g,'degree_rewire').items() if k.startswith('same_') and k!='same_topology')
    assert all(b['accepted']==b['target_swaps'] for b in r['blocks'])


def test_random_fixture_with_stalled_block_is_retained_as_invalid():
    w,g=fixture();a,r=rewire(w,g,seed_schedule()['degree_rewire'][0])
    assert r['status']=='FAILED_MIXING'
    assert any(not block['mixing_gate_pass'] for block in r['blocks'])
    invariants(w,a,g,'degree_rewire')


def test_rigid_and_failed_mixing_are_explicit_not_redrawn():
    w=np.zeros((4,4));w[0,2]=1;w[0,3]=2
    groups=[('P','left')]*2+[('Q','left')]*2
    _,r=rewire(w,groups,7);assert r['status']=='PASS' and r['blocks'][0]['rigid']
    w[1,2]=3
    _,r=rewire(w,groups,7)
    assert r['status']=='FAILED_MIXING' and r['accepted']==0 and r['attempted']>0


def test_bad_graph_rejected():
    w,g=fixture();w[0,0]=1
    with pytest.raises(ValueError):population_average(w,g)
    w[0,0]=0;w[1,0]=-1
    with pytest.raises(ValueError):weight_shuffle(w,g,7)


def test_seed_schedule_fixed_distinct_and_namespaced():
    a=seed_schedule();assert a==seed_schedule()
    assert all(len(v)==30 for v in a.values()) and len(set(sum(a.values(),[])))==60


def test_stability_native_matched_zero_radius_and_failure():
    w=np.array([[0.,2.],[1.,0.]])
    a=stability(w,'native');b=stability(w,'stability_matched')
    assert a['gain']==.5 and b['effective_radius']==pytest.approx(.6958315414466647) and b['stable']
    assert b['continuous_max_real']<0 and b['discrete_radius']<1
    z=stability(np.array([[0.,1.],[0.,0.]]),'stability_matched')
    assert z['zero_radius'] and z['gain']==.5 and z['stable']
    assert not stability(10*w,'native')['stable']
