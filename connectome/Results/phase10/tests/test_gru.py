from copy import deepcopy
import numpy as np
import pytest
from connectome.scripts.phase10.gru import GRU,Adam,train_seed,train_run,save_gru,load_gru


def samples():
    rng=np.random.default_rng(104);out=[]
    for split in ('train','validation'):
        rows=[]
        for k in range(4):
            x=rng.uniform(0,.1,(32,321));x[:8]=0;x[:, :10]=0
            if k%2:x[8:,10:]+=.4
            rows.append(dict(scenario_id=f'smoke_{split}_{k}',group_id=f'smoke_{split}_{k}',split=split,cohort=split,
                             label=k%2,role='looming' if k%2 else 'static_initial',inputs=x))
        out.append(rows)
    return out


def test_full_bptt_all_parameter_finite_differences():
    rng=np.random.default_rng(43);net=GRU(3,2,8);x=rng.normal(size=(2,7,3));y=[0,1]
    loss,g=net.loss(x,y,2,True);errors=[]
    for key,value in net.p.items():
        for index in np.ndindex(value.shape):
            old=value[index];eps=1e-5
            value[index]=old+eps;a=net.loss(x,y,2)
            value[index]=old-eps;b=net.loss(x,y,2)
            value[index]=old
            numeric=(a-b)/(2*eps)
            assert g[key][index]==pytest.approx(numeric,abs=2e-9,rel=2e-5),(key,index,numeric,g[key][index])
            errors.append(abs(numeric-g[key][index]))
    assert max(errors)<2e-9 and np.isfinite(loss)


def test_adam_matches_independent_two_step_formula_and_clips():
    p={'x':np.array([1.,-2.])};original=p['x'].copy();optimizer=Adam(p,.001,norm_limit=1.)
    grads=[np.array([3.,4.]),np.array([-2.,1.])];m=np.zeros(2);v=np.zeros(2)
    for t,g in enumerate(grads,1):
        g=g/max(1.,np.linalg.norm(g));m=.9*m+.1*g;v=.999*v+.001*g*g
        original-=.001*(m/(1-.9**t))/(np.sqrt(v/(1-.999**t))+1e-8)
        result=optimizer.step(p,{'x':grads[t-1]})
        np.testing.assert_allclose(p['x'],original,atol=1e-15,rtol=0);assert result['applied_scale']<1
    with pytest.raises(FloatingPointError):optimizer.step(p,{'x':np.array([np.nan,0.])})


def test_causal_state_clock_zero_initial_and_bounded_hidden():
    net=GRU(321,16);x=np.zeros((1,40,321));x[:,17:]=.4
    before,c=net.forward(x,True);altered=x.copy();altered[:,25:]=9
    after=net.forward(altered)
    np.testing.assert_array_equal(before[:,:26],after[:,:26])
    assert np.all(before[:,:18]==0) and np.any(before[:,18:]!=0)
    assert np.max(np.abs(c[1]))<=1 and net.parameter_count==16241


def test_loss_is_bce_on_max_causal_logit_in_window():
    x=np.random.default_rng(99).normal(size=(2,12,3));net=GRU(3,2)
    score=net.forward(x)[:,4:].max(1);expected=np.mean(np.logaddexp(0,score)-np.array([0,1])*score)
    assert net.loss(x,[0,1],4)==expected


def test_train_validation_selection_reproduces_and_roundtrips():
    train,val=samples()
    n,a=train_seed(train,val,55100,smoke=True,smoke_epochs=3,smoke_start=8)
    m,b=train_seed(train,val,55100,smoke=True,smoke_epochs=3,smoke_start=8)
    assert a==b and len(a['candidates'])==2
    for k in n.p:np.testing.assert_array_equal(n.p[k],m.p[k])
    assert a['selected']['validation_bce']==min(r['validation_bce'] for r in a['candidates'])
    record=save_gru('unit_smoke',n,dict(status='SYNTHETIC_SMOKE_ONLY',training=a))
    loaded,meta=load_gru('unit_smoke');assert record==meta
    np.testing.assert_array_equal(n.forward(train[0]['inputs'][None]),loaded.forward(train[0]['inputs'][None]))


def test_validation_never_supplies_gradient_and_no_split_family_leakage():
    train,val=samples();other=deepcopy(val)
    for r in other:r['label']=1-r['label']
    a,_=train_run(train,val,55100,.001,smoke=True,smoke_epochs=1,smoke_start=8)
    b,_=train_run(train,other,55100,.001,smoke=True,smoke_epochs=1,smoke_start=8)
    for k in a.p:np.testing.assert_array_equal(a.p[k],b.p[k])
    val[0]['group_id']=train[0]['group_id']
    with pytest.raises(ValueError):train_run(train,val,55100,.001,smoke=True)
    train,val=samples();val[0]['split']='test'
    with pytest.raises(ValueError):train_run(train,val,55100,.001,smoke=True)
    with pytest.raises(ValueError):train_run(train,samples()[1],55100,.001)


def test_validation_early_stop_returns_best_checkpoint_with_budget(monkeypatch):
    train,val=samples();calls=0;original=GRU.loss
    def loss(self,x,y,window_start=200,gradient=False):
        nonlocal calls
        if gradient:return original(self,x,y,window_start,gradient)
        calls+=1
        return float(calls)
    monkeypatch.setattr(GRU,'loss',loss)
    _,r=train_run(train,val,55100,.001,smoke=True,smoke_epochs=30,smoke_start=8)
    assert r['best_epoch']==1 and r['epochs_run']==21


def test_invalid_nonfinite_shape_seed_and_checkpoint_are_rejected():
    n=GRU(2,2)
    with pytest.raises(ValueError):n.forward(np.zeros((1,2,3)))
    with pytest.raises(ValueError):n.forward(np.full((1,2,2),np.nan))
    with pytest.raises(ValueError):GRU(2,2,parameters={'bad':np.zeros(1)})
    train,val=samples()
    with pytest.raises(ValueError):train_run(train,val,123,.001,smoke=True)


def test_numerical_trial_failures_are_reported_without_replacement(monkeypatch):
    from connectome.scripts.phase10 import gru
    original=gru.train_run;attempts=[]
    def run(train,val,seed,rate,**kwargs):
        attempts.append((seed,rate))
        if rate==.0003:raise FloatingPointError('injected numerical failure')
        return original(train,val,seed,rate,**kwargs)
    monkeypatch.setattr(gru,'train_run',run)
    train,val=samples();_,report=gru.train_seed(train,val,55100,smoke=True,smoke_start=8)
    assert attempts==[(55100,.0003),(55100,.001)]
    assert len(report['failed_trials'])==1 and report['failed_trials'][0]['replacement_seed'] is None
    assert report['selected']['learning_rate']==.001


def test_smoke_training_rejects_direct_dn_drive():
    train,val=samples();train[0]['inputs'][10,0]=.2
    with pytest.raises(ValueError):train_run(train,val,55100,.001,smoke=True,smoke_start=8)
