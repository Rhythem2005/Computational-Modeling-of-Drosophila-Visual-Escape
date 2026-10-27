"""Float64 reset-before GRU, exact BPTT and Adam; no new dependencies."""
from copy import deepcopy
import numpy as np
from .common import config, OUT, write_json, save_arrays, sha


def sigmoid(x):
    return np.exp(-np.logaddexp(0.,-x))


class GRU:
    def __init__(self, input_dim=321, hidden=16, seed=55100, parameters=None):
        if type(input_dim) is not int or input_dim<1 or type(hidden) is not int or hidden<1:
            raise ValueError('Invalid GRU dimensions')
        self.input_dim=input_dim;self.hidden=hidden;self.seed=seed
        rng=np.random.default_rng(seed)
        shapes={**{f'W{g}':(input_dim,hidden) for g in 'rzn'},**{f'U{g}':(hidden,hidden) for g in 'rzn'},
                **{f'b{g}':(hidden,) for g in 'rzn'},'w':(hidden,), 'b':(1,)}
        self.p={k:(rng.normal(size=s)/np.sqrt(s[0]) if k.startswith(('W','U')) or k=='w' else np.zeros(s)) for k,s in shapes.items()}
        if parameters is not None:
            if set(parameters)!=set(shapes) or any(parameters[k].shape!=s or parameters[k].dtype!=np.float64 or not np.isfinite(parameters[k]).all() for k,s in shapes.items()):
                raise ValueError('Invalid checkpoint parameters')
            self.p={k:v.copy() for k,v in parameters.items()}

    @property
    def parameter_count(self):return sum(p.size for p in self.p.values())

    def forward(self, inputs, cache=False):
        x=np.asarray(inputs)
        if x.dtype!=np.float64 or x.ndim!=3 or x.shape[2]!=self.input_dim or min(x.shape)<1 or not np.isfinite(x).all():
            raise ValueError('GRU input must be finite float64 (batch,time,input)')
        b,t,_=x.shape;h=np.zeros((b,t+1,self.hidden));rs=np.empty((b,t,self.hidden));zs=np.empty_like(rs);ns=np.empty_like(rs)
        p=self.p
        # Project all current inputs in one GEMM. Each step still depends only on x[k].
        projections={g:x@p['W'+g]+p['b'+g] for g in 'rzn'}
        for k in range(t):
            prev=h[:,k];r=sigmoid(projections['r'][:,k]+prev@p['Ur']);z=sigmoid(projections['z'][:,k]+prev@p['Uz'])
            n=np.tanh(projections['n'][:,k]+(r*prev)@p['Un'])
            h[:,k+1]=(1-z)*prev+z*n;rs[:,k]=r;zs[:,k]=z;ns[:,k]=n
        # State at t[k] precedes application of u[k], just as in Phase 4.
        logits=h[:,:t]@p['w']+p['b'][0]
        if not np.isfinite(logits).all():raise FloatingPointError('Nonfinite GRU output; retain failed run')
        return (logits,(x,h,rs,zs,ns)) if cache else logits

    def loss(self, inputs, labels, window_start=200, gradient=False):
        logits,cache=self.forward(inputs,cache=True);y=np.asarray(labels,dtype=np.float64)
        if y.shape!=(len(inputs),) or not set(y).issubset({0.,1.}) or type(window_start) is not int or not 0<=window_start<logits.shape[1]:
            raise ValueError('Invalid binary targets/observation window')
        indices=np.argmax(logits[:,window_start:],axis=1)+window_start
        maxima=logits[np.arange(len(y)),indices]
        loss=float(np.mean(np.logaddexp(0.,maxima)-y*maxima))
        if not gradient:return loss
        dl=np.zeros_like(logits);dl[np.arange(len(y)),indices]=(sigmoid(maxima)-y)/len(y)
        x,h,rs,zs,ns=cache;p=self.p;g={k:np.zeros_like(v) for k,v in p.items()}
        g['w']=np.einsum('bt,bth->h',dl,h[:,:-1]);g['b'][0]=dl.sum()
        dh=np.zeros_like(h);dh[:,:-1]=dl[:,:,None]*p['w']
        for k in range(x.shape[1]-1,-1,-1):
            d=dh[:,k+1];prev=h[:,k];r=rs[:,k];z=zs[:,k];n=ns[:,k]
            an=(d*z)*(1-n*n);az=(d*(n-prev))*z*(1-z)
            reset_grad=an@p['Un'].T;ar=(reset_grad*prev)*r*(1-r)
            dh[:,k]+=d*(1-z)+reset_grad*r+ar@p['Ur'].T+az@p['Uz'].T
            for gate,a,recurrent in [('n',an,r*prev),('r',ar,prev),('z',az,prev)]:
                g['W'+gate]+=x[:,k].T@a;g['U'+gate]+=recurrent.T@a;g['b'+gate]+=a.sum(0)
        return loss,g


class Adam:
    def __init__(self, parameters, rate, beta1=.9, beta2=.999, epsilon=1e-8, norm_limit=5.):
        if rate<=0 or not 0<beta1<1 or not 0<beta2<1 or epsilon<=0 or norm_limit<=0:raise ValueError('Invalid Adam settings')
        self.rate=rate;self.b1=beta1;self.b2=beta2;self.eps=epsilon;self.limit=norm_limit;self.t=0
        self.m={k:np.zeros_like(v) for k,v in parameters.items()};self.v=deepcopy(self.m)

    def step(self, parameters, gradients):
        if set(gradients)!=set(parameters) or any(gradients[k].shape!=p.shape or not np.isfinite(gradients[k]).all() for k,p in parameters.items()):
            raise FloatingPointError('Nonfinite or malformed gradient; no retry/redraw')
        norm=float(np.sqrt(sum(np.sum(v*v) for v in gradients.values())))
        if not np.isfinite(norm):raise FloatingPointError('Gradient norm overflow')
        scale=min(1.,self.limit/max(norm,1e-300));self.t+=1
        for k,p in parameters.items():
            g=gradients[k]*scale;self.m[k]=self.b1*self.m[k]+(1-self.b1)*g;self.v[k]=self.b2*self.v[k]+(1-self.b2)*g*g
            p-=self.rate*(self.m[k]/(1-self.b1**self.t))/(np.sqrt(self.v[k]/(1-self.b2**self.t))+self.eps)
            if not np.isfinite(p).all():raise FloatingPointError('Nonfinite update')
        return dict(raw_gradient_norm=norm, applied_scale=scale)


def _validate_sets(training,validation,smoke=False):
    for samples,split in ((training,'train'),(validation,'validation')):
        if not samples or any(s['split']!=split or s['cohort']!=split for s in samples):raise ValueError('Train/validation split violation')
        if {s['label'] for s in samples}!={0,1}:raise ValueError('Both classes required')
        if len({s['scenario_id'] for s in samples})!=len(samples):raise ValueError('Duplicate identity')
    if {s['group_id'] for s in training}&{s['group_id'] for s in validation}:raise ValueError('Family leakage')
    if {s['scenario_id'] for s in training}&{s['scenario_id'] for s in validation}:raise ValueError('Identity leakage')
    if not smoke:
        from .data import validate_coverage
        validate_coverage(training,'train');validate_coverage(validation,'validation')


def train_run(training, validation, seed, rate, *, smoke=False, smoke_epochs=2, smoke_start=200):
    """One predeclared run; validation chooses stopping only, never gradients."""
    _validate_sets(training,validation,smoke);c=config()
    if seed not in c['training_seeds'] or rate not in c['learning_rates']:raise ValueError('Unregistered seed/rate')
    net=GRU(c['input_dimension'],c['hidden_units'],seed);adam=Adam(net.p,rate,c['adam_beta1'],c['adam_beta2'],c['adam_epsilon'],c['gradient_norm_limit'])
    rng=np.random.default_rng(np.random.SeedSequence([seed,77]));history=[];best=float('inf');best_epoch=0;best_p=None;stale=0
    epochs=min(smoke_epochs,c['max_epochs']) if smoke else c['max_epochs'];start=smoke_start if smoke else 200
    if type(epochs) is not int or not 1<=epochs<=c['max_epochs']:raise ValueError('Invalid epoch budget')
    batch=c['batch_size']
    from connectome.scripts.phase6.encoder import load_mapping
    dn=np.array(load_mapping()['channel_index'])<0
    def inputs(rows):
        raw=np.stack([r['inputs']() if callable(r['inputs']) else r['inputs'] for r in rows])
        if raw.shape[2]!=321 or raw.dtype!=np.float64 or not np.isfinite(raw).all() or np.any(raw<0) or np.any(raw>1):raise ValueError('Invalid encoder drive')
        if np.any(raw[:,:,dn]):raise ValueError('Descending neurons must have zero direct drive')
        if not smoke and raw.shape[1]!=1000:raise ValueError('Benchmark clock changed')
        return c['input_scale']*raw
    for epoch in range(1,epochs+1):
        train_loss=0.;clipped=0
        for offset in range(0,len(training),batch):
            if offset==0:order=rng.permutation(len(training))
            rows=[training[i] for i in order[offset:offset+batch]]
            loss,grad=net.loss(inputs(rows),[r['label'] for r in rows],start,True)
            update=adam.step(net.p,grad);train_loss+=loss*len(rows);clipped+=update['applied_scale']<1
        validation_loss=0.
        for offset in range(0,len(validation),batch):
            rows=validation[offset:offset+batch]
            validation_loss+=net.loss(inputs(rows),[r['label'] for r in rows],start)*len(rows)
        validation_loss/=len(validation)
        history.append(dict(epoch=epoch,training_bce=train_loss/len(training),validation_bce=validation_loss,gradient_clipped_batches=clipped))
        if validation_loss<best:
            best=validation_loss;best_epoch=epoch;best_p=deepcopy(net.p);stale=0
        else:stale+=1
        if stale>=c['patience']:break
    net=GRU(321,16,seed,best_p)
    report=dict(seed=seed,learning_rate=rate,best_epoch=best_epoch,validation_bce=best,epochs_run=len(history),history=history,
                trainable_parameters=net.parameter_count,training_ids=[r['scenario_id'] for r in training],
                validation_ids=[r['scenario_id'] for r in validation],smoke_only=smoke,
                status='SYNTHETIC_SMOKE_ONLY' if smoke else 'TRAIN_VALIDATION_CHECKPOINT_NOT_TESTED')
    return net,report


def train_seed(training,validation,seed,**kwargs):
    runs=[];failures=[]
    for rate in config()['learning_rates']:
        try:runs.append(train_run(training,validation,seed,rate,**kwargs))
        except FloatingPointError as error:
            failures.append(dict(seed=seed,learning_rate=rate,status='FAILED_NONFINITE',error=str(error),replacement_seed=None))
    if not runs:raise FloatingPointError(f'All predeclared rate trials failed; no replacement: {failures}')
    # Stable ties prefer smaller LR; each LR starts from identical seeded weights.
    selected=min(runs,key=lambda r:(r[1]['validation_bce'],r[1]['learning_rate']))
    return selected[0],dict(selected=selected[1],candidates=[r[1] for r in runs],failed_trials=failures)


def save_gru(name, net, metadata):
    from connectome.scripts.phase5.config import validate_id
    validate_id(name)
    path=OUT/'gru'/f'{name}.npz';save_arrays(path,**net.p)
    record=dict(version='1.0.0',input_dimension=net.input_dim,hidden_units=net.hidden,seed=net.seed,parameter_count=net.parameter_count,
                parameters_sha256=sha(path),state_semantics='h[k] precedes input u[k]; scores sigmoid(readout(h[k]))',**metadata)
    write_json(path.with_suffix('.json'),record,immutable=True)
    return record


def load_gru(name):
    import json
    from connectome.scripts.phase5.config import validate_id
    validate_id(name);p=OUT/'gru'/f'{name}.npz';record=json.loads(p.with_suffix('.json').read_text())
    if sha(p)!=record['parameters_sha256']:raise ValueError('Corrupt GRU checkpoint')
    with np.load(p,allow_pickle=False) as f:
        net=GRU(record['input_dimension'],record['hidden_units'],record['seed'],{k:f[k].copy() for k in f.files})
    if net.parameter_count!=record['parameter_count']:raise ValueError('Parameter count mismatch')
    return net,record
