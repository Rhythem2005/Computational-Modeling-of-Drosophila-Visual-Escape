"""Shared causal inputs for reference, rate controls, minimal controls and GRU."""
import time
import numpy as np
from .common import config, digest
from .data import validate_drive, array_digest
from .networks import load_network
from .gru import sigmoid
from connectome.scripts.phase4 import dynamics


def rate_trace(drive,pipeline,weights,condition):
    validate_drive(drive,pipeline);c=config();n=drive.shape[1]
    if weights.shape!=(n,n) or not np.isfinite(weights).all() or np.any(weights<0) or np.diag(weights).any():raise ValueError('Invalid control weights')
    if not condition['stable']:raise FloatingPointError('Unstable architecture: retain failure, never redraw')
    start=time.perf_counter()
    times,states=dynamics.simulate(weights,np.full(n,c['tau_ms']),condition['gain'],c['dt_ms'],c['duration_ms'],
                                   lambda t,n: c['input_scale']*drive[int(t)],clip_max=50.,noise_std=0.)
    if not np.isfinite(states).all():raise FloatingPointError('Nonfinite activity')
    pre=condition['gain']*(states[:-1]@weights.T)+c['input_scale']*drive
    clipped=float(np.mean(pre>50.))
    by_id={b:i for i,b in enumerate(pipeline.circuit.body_ids)}
    score=states[:-1,[by_id[10010],by_id[10001]]].mean(1)
    dn=pipeline.circuit.get_dn_indices()
    return dict(times_ms=times[:-1],score=score,states=states,dn_activity=states[:-1,dn],
                diagnostics=dict(finite=True,runtime_s=time.perf_counter()-start,activity_min=float(states.min()),activity_max=float(states.max()),
                                 input_scaled_max=float((.4*drive).max()),clipped_fraction=clipped,linear_regime_valid=clipped<=.01,
                                 input_sha256=array_digest(drive),trainable_parameters=0,condition=condition))


def minimal_features(drive,pipeline):
    validate_drive(drive,pipeline);assigned=np.array(pipeline.encoder.mapping['channel_index'])
    channels=np.column_stack([drive[:,assigned==k].mean(1) for k in (0,1)])
    filtered=np.zeros_like(channels)
    for k in range(999):filtered[k+1]=filtered[k]+.1*(-filtered[k]+.4*channels[k])
    return .4*channels.mean(1),filtered


def score_model(model_id,drive,pipeline,*,condition='native',gru=None,linear=None):
    """Metadata/labels/geometry are not arguments to a model's forward pass."""
    validate_drive(drive,pipeline)
    if model_id=='feature_only':return minimal_features(drive,pipeline)[0]
    if model_id=='linear_temporal':
        from connectome.scripts.phase8.completion.controls import linear_score
        if linear is None:raise ValueError('Training-only linear weights required')
        return linear_score(minimal_features(drive,pipeline)[1],linear)
    if model_id=='gru':
        if gru is None or gru.input_dim!=321 or gru.hidden!=16:raise ValueError('Expected the registered GRU')
        return sigmoid(gru.forward(.4*drive[None]))[0]
    w,setting,_=load_network(model_id,pipeline.circuit,condition)
    return rate_trace(drive,pipeline,w,setting)['score']


def freeze_identity(model_id,model_hash,condition,mapping):
    c=config()
    if condition not in ('native','stability_matched') or mapping not in ['uniform_population',*c['mapping_seeds']]:raise ValueError('Unregistered condition/mapping')
    return dict(model_id=model_id,model_sha256=model_hash,gain_condition=condition,mapping=mapping,
                config_sha256=digest(c),duration_ms=1000,dt_ms=1,input_scale=.4,persistence_ms=20,
                decoder='first_event_latched_closed_20ms_half_open_episode',initial_state='zeros',warmup_ms=0)
