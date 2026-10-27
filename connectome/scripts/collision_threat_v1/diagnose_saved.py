"""Bounded Stage A: saved-image measurements only, never model or world execution."""
from dataclasses import asdict
from pathlib import Path
import numpy as np
import yaml
from .common import ROOT,SOURCE_RUN,PLAN,read,sha,write,MAX_SAVED_EPISODES
from .features import camera_from_config,extract,available_tick

FLOAT_COLUMNS=('timestamp_s','radius_px','centroid_x_px','centroid_y_px','normalized_x','normalized_y',
               'bearing_rad','half_extent_rad','radius_rate_px_s','centroid_x_rate_px_s',
               'centroid_y_rate_px_s','bearing_rate_rad_s','extent_rate_rad_s','interval_s')
BOOL_COLUMNS=('measurement_valid','motion_valid','border_contact','foreground_dominant','timestamp_gap')

def verify_inputs():
    saved=read(PLAN/'evidence_snapshot.json')
    if sha(PLAN/'README.md')!=saved['plan_sha256']:raise ValueError('Approved plan changed')
    for name,h in saved['evidence_sha256'].items():
        if sha(SOURCE_RUN/name)!=h:raise ValueError(f'Saved evidence changed: {name}')
    for name,h in saved['production_pointers_sha256'].items():
        if sha(ROOT/name)!=h:raise ValueError(f'Production state changed since planning: {name}')
    manifest=read(SOURCE_RUN/'manifest.json')
    for name,h in manifest['source_hashes'].items():
        if sha(ROOT/name)!=h:raise ValueError(f'Executed behavioral source changed: {name}')
    jobs=[j for j in manifest['jobs'] if j['repeat']==0]
    if len(jobs)!=MAX_SAVED_EPISODES or len({j['episode_id'] for j in jobs})!=len(jobs):
        raise ValueError('Saved unique episode roster changed')
    summary=read(SOURCE_RUN/'summary.json')
    if summary['attempts']!=182 or summary['unique_episodes']!=91 or summary['status']!='COMPLETE_ENGINEERING':
        raise ValueError('Source engineering run is not complete')
    return manifest,summary,jobs

def load_source(job,manifest,summary):
    ident=job['episode_id']
    if Path(ident).name!=ident:raise ValueError('Unsafe episode ID')
    metadata_path=SOURCE_RUN/'episodes'/f'{ident}.json'
    npz_path=metadata_path.with_suffix('.npz')
    metadata=read(metadata_path)
    if sha(npz_path)!=metadata['arrays_sha256']:raise ValueError(f'Episode hash changed: {ident}')
    scenario=next(s for s in manifest['scenarios'] if s['scenario_id']==job['scenario_id'])
    model=next(r for r in manifest['roster'][job['mapping']] if r['id']==job['model_id'])
    group=summary['groups'][job['mapping']+'/'+job['model_id']]
    recorded=next(e for e in group['episodes'] if e['id']==ident)
    if (metadata['config']!=manifest['world_config'] or metadata['scenario']!=scenario
            or metadata['model']!=job['model_id'] or metadata['mapping']!=job['mapping']
            or metadata['threshold']!=model['threshold']
            or metadata['metrics']!={k:v for k,v in recorded.items() if k!='id'}):
        raise ValueError('Source metadata differs from source manifest/summary')
    with np.load(npz_path,allow_pickle=False) as f:
        if f['schema_version'].item()!='behavior_1.0':raise ValueError('Unknown source schema')
        arrays={k:f[k].copy() for k in ('frames','frame_timestamps_s','channels','frame_valid',
                'decision_times_ms','score','sustained_score','escape_event','near_or_behind')}
    return metadata,arrays,dict(metadata_sha256=sha(metadata_path),npz_sha256=sha(npz_path))

def save_features(output,ident,rows,source,source_arrays):
    arrays={k:np.array([np.nan if r[k] is None else r[k] for r in rows],dtype=np.float64) for k in FLOAT_COLUMNS}
    arrays.update({k:np.array([r[k] for r in rows],dtype=bool) for k in BOOL_COLUMNS})
    for k in ('area_px','component_count'):
        arrays[k]=np.array([r[k] for r in rows],dtype=np.int64)
    arrays['reason_codes']=np.array(['|'.join(r['reasons']) for r in rows])
    ticks=np.array([available_tick(r['timestamp_s']) for r in rows],dtype=np.int64)
    eligible=ticks<len(source_arrays['decision_times_ms'])
    arrays.update(first_available_ms=ticks,source_has_eligible_decision=eligible,
                  original_channels=source_arrays['channels'],original_frame_valid=source_arrays['frame_valid'])
    for k in ('score','sustained_score'):
        aligned=np.full(len(rows),np.nan)
        aligned[eligible]=source_arrays[k][ticks[eligible]]
        arrays['original_'+k+'_at_first_available_tick']=aligned
    path=output/'features'/f'{ident}.npz';path.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(path,schema_version=np.array('causal_image_features_1.0'),**arrays)
    # Explicit missingness: NaNs are storage markers only; None/flags/reasons
    # distinguish undefined observations from nonfinite implementation defects.
    for key in FLOAT_COLUMNS:
        defined=np.array([r[key] is not None for r in rows])
        assert np.isfinite(arrays[key][defined]).all()
        assert np.isnan(arrays[key][~defined]).all()
    write(path.with_suffix('.json'),dict(source=source,features_sha256=sha(path),
          undefined_float_storage='NaN with validity/reason masks; extractor outputs None',
          rows=rows,source_model_inference_performed=False))
    return sha(path)

def first_tick(rows,predicate):
    return next((available_tick(r['timestamp_s']) for r in rows if predicate(r)),None)

def pair_report(a,b):
    n=min(len(a['arrays']['frames']),len(b['arrays']['frames']))
    ta=a['arrays']['frame_timestamps_s'][:n];tb=b['arrays']['frame_timestamps_s'][:n]
    np.testing.assert_array_equal(ta,tb)
    pixels=np.any(a['arrays']['frames'][:n]!=b['arrays']['frames'][:n],axis=(1,2))
    channels=np.any(a['arrays']['channels'][:n]!=b['arrays']['channels'][:n],axis=1)
    def first(mask):
        where=np.flatnonzero(mask)
        return None if not len(where) else available_tick(ta[where[0]])
    return dict(compared_common_frames=n,first_different_pixels_available_ms=first(pixels),
                first_different_channels_available_ms=first(channels),
                exactly_equal_pixel_frames=int((~pixels).sum()),exactly_equal_channel_frames=int((~channels).sum()),
                maximum_channel_absolute_difference=float(np.abs(a['arrays']['channels'][:n]-b['arrays']['channels'][:n]).max()),
                note='No-action paths only; no post-contact padding or threshold/model fitting.')

def run(output,budget):
    manifest,summary,jobs=verify_inputs()
    encoder_path=ROOT/'connectome/Results/phase6/encoder_config.yaml'
    camera=camera_from_config(manifest['world_config'],yaml.safe_load(encoder_path.read_text()))
    no_action={};validity={};feature_hashes={};primary_alignment=[]
    for index,job in enumerate(jobs,1):
        budget.check()
        metadata,arrays,bindings=load_source(job,manifest,summary)
        # The extractor receives ONLY pixels, seconds, and whitelisted Camera.
        rows=extract(arrays['frames'],arrays['frame_timestamps_s'],camera)
        ident=job['episode_id']
        feature_hashes[ident]=save_features(output,ident,rows,bindings,arrays)
        validity[ident]=dict(frame_count=len(rows),measurement_valid_frames=sum(r['measurement_valid'] for r in rows),
            motion_valid_frames=sum(r['motion_valid'] for r in rows),
            empty_frames=sum(r['area_px']==0 for r in rows),multiple_component_frames=sum(r['component_count']>1 for r in rows),
            border_frames=sum(r['border_contact'] for r in rows),foreground_dominant_frames=sum(r['foreground_dominant'] for r in rows),
            timestamp_gap_frames=sum(r['timestamp_gap'] for r in rows),
            saved_renderer_near_or_behind_frames=int(np.count_nonzero(arrays['near_or_behind'])),
            depth_inferred_by_extractor=False,source_bindings=bindings)
        if job['mapping']=='uniform_population':
            m=metadata['metrics'];request=m['first_request_ms']
            pre=[r for r in rows if request is None or available_tick(r['timestamp_s'])<=request]
            primary_alignment.append(dict(episode_id=ident,scenario_id=job['scenario_id'],model_id=job['model_id'],
                danger=m['danger'],original_request_ms=request,original_actuation_ms=m['scheduled_actuation_ms'],
                original_first_motion_ms=m['first_motion_ms'],stationary_contact_ms=m['stationary_contact_ms'],
                first_usable_motion_ms=first_tick(rows,lambda r:r['motion_valid']),
                first_nonzero_bearing_motion_ms=first_tick(rows,lambda r:r['motion_valid'] and r['bearing_rate_rad_s']!=0),
                first_positive_extent_growth_ms=first_tick(rows,lambda r:r['motion_valid'] and r['extent_rate_rad_s']>0),
                last_available_before_request=None if request is None or not pre else pre[-1],
                request_to_stationary_contact_ms=None if request is None or m['stationary_contact_ms'] is None else m['stationary_contact_ms']-request))
            if job['model_id']=='no_action':
                no_action[job['scenario_id']]=dict(rows=rows,arrays=arrays,metrics=m)
        write(output/'progress.json',dict(saved_unique_trajectories_processed=index,total=91,
              new_simulations=0,new_model_inference=0,current=ident))
        print(f'{index}/91 saved trajectory {ident}',flush=True)
    assert len(no_action)==5
    timelines=[]
    for case,data in no_action.items():
        circuit=next(e for e in primary_alignment if e['scenario_id']==case and e['model_id']=='circuit')
        request=circuit['original_request_ms']
        rows=data['rows'];prior=[r for r in rows if request is not None and available_tick(r['timestamp_s'])<=request]
        timelines.append(dict(scenario_id=case,danger=data['metrics']['danger'],source='no_action',
            frames=len(rows),first_motion_measurement_ms=first_tick(rows,lambda r:r['motion_valid']),
            first_nonzero_bearing_motion_ms=first_tick(rows,lambda r:r['motion_valid'] and r['bearing_rate_rad_s']!=0),
            first_positive_extent_growth_ms=first_tick(rows,lambda r:r['motion_valid'] and r['extent_rate_rad_s']>0),
            legacy_circuit_request_ms=request,legacy_actuation_ms=circuit['original_actuation_ms'],
            legacy_first_displacement_ms=circuit['original_first_motion_ms'],
            stationary_contact_ms=data['metrics']['stationary_contact_ms'],
            last_motion_record_before_legacy_request=None if not prior else prior[-1],
            apparent_warning_margin_is_not_last_safe_action_proof=True))
    near=next(t for t in timelines if t['scenario_id']=='world_near_miss')
    near_valid=(near['first_nonzero_bearing_motion_ms'] is not None and
                near['first_nonzero_bearing_motion_ms']<near['legacy_circuit_request_ms'])
    danger_valid=all(t['last_motion_record_before_legacy_request'] is not None and
                     t['last_motion_record_before_legacy_request']['motion_valid'] for t in timelines if t['danger'])
    result=dict(status='COMPLETE_SAVED_DATA_DIAGNOSTIC',saved_unique_trajectories_processed=len(jobs),
        camera=asdict(camera),encoder_segmentation_config_sha256=sha(encoder_path),
        timeline=timelines,primary_controller_alignment=primary_alignment,
        primary_head_on_vs_near_miss=pair_report(no_action['world_head_on'],no_action['world_near_miss']),
        image_motion_available_before_legacy_request=near_valid and danger_valid,
        stage_a_review='PROCEED_TO_EXACT_RULE_SPECIFICATION' if near_valid and danger_valid else 'STOP_AND_REVIEW_INFORMATION_OR_LATENCY',
        stage_b_execution_enabled=False,rule_calibration_performed=False,decision_threshold_searches=0,
        diagnostic_nonzero_comparisons='Descriptive equality/sign checks only, not a controller or calibrated classification rule',
        new_simulations=0,new_model_inference=0,new_training=0,new_calibration=0,held_out_evaluations=0,
        source_manifest_sha256=sha(SOURCE_RUN/'manifest.json'),feature_files_sha256=feature_hashes)
    write(output/'validity_report.json',validity);write(output/'information_audit.json',result)
    report(output,result,validity)
    plot(output,no_action,timelines)
    budget.check()
    return result

def report(output,result,validity):
    lines=['# Stage A — saved-image information and timing audit','',
           'Processed 91 unique saved trajectories. No model inference, classifier fitting, threshold search, world simulation, training or held-out evaluation occurred.',
           'The five uniform no-action paths provide the primary information diagnostic. Their dangerous trajectories end at collision; no post-contact frames were fabricated.','',
           '| Known case | First usable motion measurement ms | First nonzero bearing motion ms | First positive extent growth ms | Legacy circuit request ms | Stationary contact ms |',
           '| --- | --- | --- | --- | --- | --- |']
    for t in result['timeline']:
        lines.append('| '+' | '.join(str(t[k]) for k in ('scenario_id','first_motion_measurement_ms',
                     'first_nonzero_bearing_motion_ms','first_positive_extent_growth_ms','legacy_circuit_request_ms','stationary_contact_ms'))+' |')
    p=result['primary_head_on_vs_near_miss']
    lines += ['',f"Head-on and near-miss images first differ at an available tick of {p['first_different_pixels_available_ms']} ms; their original size/growth channels first differ at {p['first_different_channels_available_ms']} ms. They are not exactly identical observations.",
              '',f"Stage A review: **{result['stage_a_review']}**. Image motion is available before the legacy request: {result['image_motion_available_before_legacy_request']}.",
              'This supports constructing a candidate rule, not an information-theoretic proof, a fitted classifier result, or a demonstrated safe later request time.',
              'The primary encoder does not explicitly retain centroid/bearing motion. More training on its original task is not established as a remedy.',
              '', 'Missing image evidence remains unknown. Empty masks cannot distinguish absence, near-plane disappearance, or an object behind the camera. Renderer depth diagnostics are saved audit references only and do not enter the extractor.',
              'All episodes remain included. Unsupported-image exposure is reported in validity_report.json; it is not used for outcome-dependent exclusions.',
              '', 'Stage B remains disabled until the exact candidate equations, assumptions, persistence and finite calibration manifest receive the reserved review/authorization. No prototype episode budget has been used.',
              'The original 45 completed trials and partial checkpoint remain preserved. The earlier five fixtures remain development evidence; no generalization or biological claim is made.','']
    (output/'information_audit.md').write_text('\n'.join(lines))

def plot(output,no_action,timelines):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,1,figsize=(10,7),sharex=True)
    for case,data in no_action.items():
        rows=data['rows'];ts=np.array([r['timestamp_s']*1000 for r in rows])
        for ax,key in zip(axes,('bearing_rad','half_extent_rad')):
            vals=[np.nan if r[key] is None else r[key] for r in rows]
            ax.plot(ts,vals,label=case.replace('world_',''))
    axes[0].set_ylabel('Image bearing (rad)');axes[1].set_ylabel('Angular half-extent proxy (rad)')
    axes[1].set_xlabel('Available physical frame timestamp (ms)')
    axes[0].legend(ncol=3);axes[0].set_title('Saved no-action paths: observed image measurements only')
    for ax in axes:
        ax.axvline(239,color='gray',linestyle='--',linewidth=1,label='legacy circuit request')
        ax.grid(alpha=.25)
    fig.text(.5,.01,'Dashed line: saved circuit request at 239 ms. Missing/unsupported measurements are gaps. Known fixtures only.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.03,1,1));fig.savefig(output/'saved_image_measurements.png',dpi=150);plt.close(fig)
