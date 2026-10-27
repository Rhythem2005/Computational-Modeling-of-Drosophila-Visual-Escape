"""Block-constrained graph controls, diagnostics, and immutable model bank."""
import numpy as np
from .common import OUT, config, digest, write_json, save_arrays, sha


def labels(circuit):
    return [(circuit.type_map[b], circuit.side_map[b]) for b in circuit.body_ids]


def blocks(matrix, groups):
    if matrix.dtype != np.float64 or matrix.shape != (len(groups),len(groups)) or not np.all(np.isfinite(matrix)) or np.any(matrix < 0) or np.any(np.diag(matrix)):
        raise ValueError('Expected finite unsigned W[post,pre] with no diagonal')
    for post in sorted(set(groups)):
        rows = np.array([i for i,g in enumerate(groups) if g == post])
        for pre in sorted(set(groups)):
            cols = np.array([i for i,g in enumerate(groups) if g == pre])
            rr,cc = np.meshgrid(rows,cols,indexing='ij')
            eligible = rr != cc
            yield f'{pre[0]}:{pre[1]}->{post[0]}:{post[1]}', rr[eligible], cc[eligible]


def population_average(w, groups):
    out=np.zeros_like(w)
    for _,r,c in blocks(w,groups):
        if len(r): out[r,c]=w[r,c].sum()/len(r)
    return out


def weight_shuffle(w, groups, seed):
    rng=np.random.default_rng(seed);out=w.copy()
    for _,r,c in blocks(w,groups):
        nonzero=w[r,c]>0;r,c=r[nonzero],c[nonzero]
        out[r,c]=rng.permutation(w[r,c])
    return out


def rewire(w, groups, seed, swaps_per_edge=20, attempts_per_edge=400, checkpoints=20):
    if type(swaps_per_edge) is not int or swaps_per_edge<1 or type(attempts_per_edge) is not int or attempts_per_edge<swaps_per_edge:
        raise ValueError('Invalid fixed mixing budget')
    rng=np.random.default_rng(seed);out=np.zeros_like(w);reports=[]
    for name,r,c in blocks(w,groups):
        nz=w[r,c]>0;posts=r[nz].copy();pres=c[nz].copy();weights=w[posts,pres].copy();m=len(posts)
        if not m: continue
        initial=set(zip(posts.tolist(),pres.tolist()));edges=set(initial)
        rigid = m<2 or len(set(posts))<2 or len(set(pres))<2 or m==len(r)
        accepted=attempted=0;target=0 if rigid else swaps_per_edge*m;history=[]
        next_check=max(1,target//checkpoints)
        while accepted<target and attempted<attempts_per_edge*m:
            a,b=rng.integers(m,size=2);attempted+=1
            p,q=int(posts[a]),int(posts[b]);s,t=int(pres[a]),int(pres[b])
            if p==q or s==t or p==t or q==s or (p,t) in edges or (q,s) in edges: continue
            edges.remove((p,s));edges.remove((q,t));edges.add((p,t));edges.add((q,s))
            pres[a],pres[b]=t,s;accepted+=1
            if accepted>=next_check:
                history.append(dict(accepted=accepted, original_edge_overlap=len(edges & initial)/m))
                next_check+=max(1,target//checkpoints)
        # Weights are separately randomized after topology swaps: only block
        # multisets, not neuron strengths or an edge's original weight, are fixed.
        out[posts,pres]=rng.permutation(weights)
        changed=any(h['original_edge_overlap']<1 for h in history)
        valid=rigid or (accepted==target and changed)
        reports.append(dict(block=name, edges=m, rigid=rigid, rigidity_reason='single endpoint / complete eligible block / fewer than two edges' if rigid else None,
                            target_swaps=target, accepted=accepted, attempted=attempted,
                            acceptance_rate=accepted/attempted if attempted else None,
                            final_original_edge_overlap=len(edges & initial)/m, checkpoints=history, mixing_gate_pass=bool(valid)))
    return out,dict(status='PASS' if all(r['mixing_gate_pass'] for r in reports) else 'FAILED_MIXING',
                    blocks=reports, accepted=sum(r['accepted'] for r in reports), attempted=sum(r['attempted'] for r in reports),
                    caveat='Finite swap/turnover diagnostics are not a proof of independent uniform graph sampling; rigid blocks cannot randomize.')


def invariants(reference, candidate, groups, kind):
    list(blocks(candidate,groups))  # shape, sign, finite, loop validation
    if candidate.shape != reference.shape: raise ValueError('Node dimension changed')
    checks=dict(no_self_loops=not np.diag(candidate).any(), finite=bool(np.isfinite(candidate).all()),
                same_block_totals=True, same_block_weight_multisets=True,
                same_topology=bool(np.array_equal(reference>0,candidate>0)),
                same_in_out_degrees=bool(np.array_equal((reference>0).sum(0),(candidate>0).sum(0)) and np.array_equal((reference>0).sum(1),(candidate>0).sum(1))))
    for _,r,c in blocks(reference,groups):
        a,b=reference[r,c],candidate[r,c]
        checks['same_block_totals'] &= bool(np.isclose(a.sum(),b.sum(),rtol=1e-12,atol=1e-12))
        checks['same_block_weight_multisets'] &= bool(np.array_equal(np.sort(a[a>0]),np.sort(b[b>0])))
        if kind=='population_average' and len(r) and not np.all(b==b[0]): raise ValueError('Block is not uniform')
    required=['finite','no_self_loops','same_block_totals']
    if kind in ('weight_shuffle','degree_rewire'): required+=['same_block_weight_multisets','same_in_out_degrees']
    if kind=='weight_shuffle': required+=['same_topology']
    if not all(checks[k] for k in required): raise ValueError(f'Graph invariant failed: {checks}')
    checks['max_in_strength_change']=float(np.max(np.abs(candidate.sum(1)-reference.sum(1))))
    checks['max_out_strength_change']=float(np.max(np.abs(candidate.sum(0)-reference.sum(0))))
    return checks


def stability(w, condition, fixed_gain=.5, target=.6958315414466647, tau=10., dt=1.):
    if condition not in ('native','stability_matched'): raise ValueError('Unknown gain condition')
    if w.ndim!=2 or w.shape[0]!=w.shape[1] or not np.isfinite(w).all(): raise ValueError('Invalid matrix')
    eigen=np.linalg.eigvals(w);radius=float(np.max(np.abs(eigen)))
    gain=target/radius if condition=='stability_matched' and radius>0 else fixed_gain
    continuous=(-1+gain*eigen)/tau;discrete=1+dt*continuous
    return dict(condition=condition, gain=float(gain), unscaled_radius=radius, effective_radius=float(radius*gain),
                continuous_max_real=float(continuous.real.max()), discrete_radius=float(np.abs(discrete).max()),
                stable=bool(continuous.real.max()<0 and np.abs(discrete).max()<1), zero_radius=radius==0,
                target=target if condition=='stability_matched' else None,
                recurrent_matrix_rescale=gain/fixed_gain)


def seed_schedule():
    c=config()
    return {kind:[int(np.random.SeedSequence([c['design_seed'],10,k,i]).generate_state(1)[0]) for i in range(c['null_count'])]
            for k,kind in enumerate(('weight_shuffle','degree_rewire'),1)}


def build_bank(circuit):
    c=config();w=circuit.W_norm;groups=labels(circuit);schedule=seed_schedule()
    write_json(OUT/'seed_schedule.json',schedule,immutable=True)
    definitions=[('circuit','circuit',None),('population_average','population_average',None)]
    definitions += [(f'{kind}_{i:02d}',kind,seed) for kind,seeds in schedule.items() for i,seed in enumerate(seeds)]
    bank=[]
    for name,kind,seed in definitions:
        mixing=None
        if kind=='circuit': matrix=w.copy()
        elif kind=='population_average': matrix=population_average(w,groups)
        elif kind=='weight_shuffle': matrix=weight_shuffle(w,groups,seed)
        else: matrix,mixing=rewire(w,groups,seed,c['rewiring_swaps_per_edge'],c['rewiring_attempts_per_edge'],c['rewiring_checkpoints'])
        inv=invariants(w,matrix,groups,kind)
        path=OUT/'networks'/f'{name}.npz';save_arrays(path,weights=matrix,body_ids=np.array(circuit.body_ids,dtype=np.int64))
        gain_conditions={v:stability(matrix,v,c['gain'],c['target_radius'],c['tau_ms'],c['dt_ms']) for v in ('native','stability_matched')}
        entry=dict(model_id=name,kind=kind,seed=seed,weights_sha256=sha(path),path=str(path.relative_to(OUT)),
                   invariants=inv,mixing=mixing,conditions=gain_conditions,trainable_parameters=0,threshold_parameters=1,
                   eligible_for_use=(mixing is None or mixing['status']=='PASS'))
        write_json(OUT/'networks'/f'{name}.json',entry,immutable=True);bank.append(entry)
        print('Built',name,'mixing',None if mixing is None else mixing['status'],flush=True)
    write_json(OUT/'network_bank.json',bank,immutable=True)
    return bank


def load_network(model_id, circuit, condition='native'):
    import json
    bank=json.loads((OUT/'network_bank.json').read_text());found=[r for r in bank if r['model_id']==model_id]
    if len(found)!=1: raise ValueError('Unknown bank model')
    row=found[0];path=OUT/row['path']
    if sha(path)!=row['weights_sha256'] or not row['eligible_for_use']: raise ValueError('Corrupt or failed-mixing model')
    with np.load(path,allow_pickle=False) as f:
        if not np.array_equal(f['body_ids'],np.asarray(circuit.body_ids,dtype=np.int64)): raise ValueError('Body-ID order mismatch')
        weights=f['weights'].copy()
    if condition not in row['conditions']: raise ValueError('Unknown condition')
    return weights,row['conditions'][condition],row
