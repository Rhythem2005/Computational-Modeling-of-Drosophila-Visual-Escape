"""New version of the causal orchestration; frozen world and encoder unchanged."""
import numpy as np
from connectome.scripts.phase9.world import World,render_camera
from .driver import Driver

class Runner:
    def __init__(self,pipeline,config,camera,legacy_rows,prior):
        self.pipeline=pipeline;self.config=config;self.camera=camera;self.legacy_rows=legacy_rows;self.prior=prior

    def run(self,scenario,model,heartbeat=lambda:None):
        c=self.config;world=World(c,scenario)
        if world.done:raise ValueError('Existing fixtures must start nonterminal')
        driver=Driver(model,self.pipeline,self.camera,self.legacy_rows,self.prior)
        frame,diag=render_camera(c,world.fly,world.obstacles,world.radii)
        frames=[frame];times=[0.];rendering=[diag];processed=0;frame_number=1
        drive=np.zeros(321,dtype=np.float64)
        states=[driver.state_vector()];world_times=[0.];flies=[world.fly.copy()]
        obstacles=[world.obstacles.copy()];speeds=[0.];drives=[];indices=[];outputs=[]
        while not world.done:
            k=len(outputs)
            if k%100==0:heartbeat()
            if world.time_ms!=k or k>=1000:raise ValueError('Controller/world clock divergence')
            available=int(np.searchsorted(np.array(times),k/1000,side='right'))
            if available!=processed:
                encoded=self.pipeline.encoder.encode(np.stack(frames[:available]),np.array(times[:available]))
                drive=encoded.drive[-1].copy()
                for j in range(processed,available):driver.observe(frames[j],times[j])
                processed=available
            out=driver.sample(k,drive)
            if out['escape_event']:world.request(0.)
            outputs.append(out);drives.append(drive.copy());indices.append(available-1)
            segment=world.step()
            world_times.append(world.time_ms);flies.append(world.fly.copy())
            obstacles.append(world.obstacles.copy());speeds.append(world.speed)
            while frame_number/c['camera_fps']<=world.time_ms/1000 and frame_number/c['camera_fps']<1:
                ts=frame_number/c['camera_fps']
                alpha=(ts*1000-segment['start_ms'])/(segment['end_ms']-segment['start_ms'])
                fly=segment['fly_start']+alpha*(segment['fly_end']-segment['fly_start'])
                obs=segment['obstacles_start']+alpha*(segment['obstacles_end']-segment['obstacles_start'])
                frame,diag=render_camera(c,fly,obs,world.radii)
                frames.append(frame);times.append(ts);rendering.append(diag);frame_number+=1
            if world.time_ms==k+1:
                driver.advance(drive);states.append(driver.state_vector())
            elif not world.terminated:raise ValueError('Fractional endpoint without termination')
        arrays=dict(world_times_ms=np.array(world_times),fly_position=np.array(flies),
             obstacle_positions=np.array(obstacles),speed=np.array(speeds),frames=np.stack(frames),
             frame_timestamps_s=np.array(times),decision_times_ms=np.arange(len(outputs),dtype=np.float64),
             decision_drive_unscaled=np.array(drives),decision_input_scaled=.4*np.array(drives),
             decision_frame_indices=np.array(indices,dtype=np.int64),controller_states=np.array(states),
             controller_state_times_ms=np.arange(len(states),dtype=np.float64),
             body_ids=np.asarray(self.pipeline.circuit.body_ids,dtype=np.int64),
             near_or_behind=np.array([d['near_or_behind'] for d in rendering],dtype=np.int64),
             projected_objects=np.array([len(d['projected']) for d in rendering],dtype=np.int64))
        for key in outputs[0]:arrays[key]=np.array([o[key] for o in outputs])
        encoded=self.pipeline.encoder.encode(arrays['frames'],arrays['frame_timestamps_s'])
        arrays.update(channels=encoded.channels,frame_drive=encoded.drive,frame_valid=encoded.diagnostics['valid'])
        np.testing.assert_array_equal(arrays['decision_drive_unscaled'],encoded.drive[arrays['decision_frame_indices']])
        np.testing.assert_array_equal(arrays['decision_frame_indices'],
            np.searchsorted(arrays['frame_timestamps_s'],arrays['decision_times_ms']/1000,side='right')-1)
        records=driver.frame_records;measurements=[r['measurement'] for r in records]
        arrays['measurement_timestamps_s']=np.array([m['timestamp_s'] for m in measurements])
        for key in ('measurement_valid','motion_valid','border_contact','foreground_dominant','timestamp_gap'):
            arrays['measurement_'+key]=np.array([m[key] for m in measurements],dtype=bool)
        for key in ('radius_px','centroid_x_px','bearing_rad','half_extent_rad','bearing_rate_rad_s','extent_rate_rad_s'):
            arrays['measurement_'+key]=np.array([np.nan if m[key] is None else m[key] for m in measurements])
        arrays['measurement_reasons']=np.array(['|'.join(m['reasons']) for m in measurements])
        for key in ('t_closest_s','d_closest_in_object_radii'):
            arrays['estimate_'+key]=np.array([np.nan if r['estimate'] is None or r['estimate'][key] is None else r['estimate'][key] for r in records])
        metrics=world.metrics();request=world.request_ms
        pre=np.ones(len(measurements),dtype=bool) if request is None else arrays['measurement_timestamps_s']<=request/1000
        valid=arrays['measurement_measurement_valid'];motion=arrays['measurement_motion_valid']
        legacy_valid=arrays['frame_valid'];lpre=np.ones(len(legacy_valid),dtype=bool) if request is None else arrays['frame_timestamps_s']<=request/1000
        direct=np.array(self.pipeline.encoder.mapping['channel_index'])<0
        metrics.update(model=model,mapping='uniform_population',internal_request_ms=driver.internal_request_ms,
            physical_request_ms=request,gate_delay_ms=None if request is None or driver.internal_request_ms is None else request-driver.internal_request_ms,
            physical_request_reason=next((o['physical_reason'] for o in outputs if o['escape_event']),None),
            unknown_decision_ticks=driver.unknown_ticks,fallback_events=driver.fallback_count,
            encoder_valid_fraction=float(legacy_valid.mean()),encoder_valid_frames=int(legacy_valid.sum()),frame_count=len(legacy_valid),
            pre_request_valid_fraction=float(legacy_valid[lpre].mean()),encoder_cap_fraction=float(np.mean(encoded.channels>=1)),
            perception_frame_count=len(measurements),measurement_valid_frames=int(valid.sum()),motion_valid_frames=int(motion.sum()),
            pre_request_measurement_frames=int(pre.sum()),pre_request_measurement_valid_frames=int(valid[pre].sum()),
            border_contact_frames=int(arrays['measurement_border_contact'].sum()),
            near_or_behind_frame_count=int(np.count_nonzero(arrays['near_or_behind'])),
            whole_episode_encoder_valid=bool(legacy_valid.all()),direct_dn_input_max=float(encoded.drive[:,direct].max()),
            finite_controller_state=bool(np.isfinite(arrays['controller_states']).all()),
            threat_estimator='point observer; constant unknown object radius and relative velocity; not finite-fly safety proof' if driver.rule else None,
            new_calibration=False)
        metrics.update(known_size_prior_active=driver.finite,
            known_size_prior_matches=None if not driver.finite else bool(c['fly_radius']==self.prior.self_radius and all(ob['radius']==self.prior.object_radius for ob in scenario['obstacles'])),
            retirement_events=int(arrays['retirement_event'].sum()),rearm_events=int(arrays['rearm_event'].sum()),
            candidate_generation_events=int(arrays['candidate_generation_event'].sum()),
            retirement_times_ms=arrays['decision_times_ms'][arrays['retirement_event']].tolist(),
            rearm_times_ms=arrays['decision_times_ms'][arrays['rearm_event']].tolist(),
            unknown_after_retirement_ticks=int(arrays['unknown_after_retirement'].sum()))
        if driver.finite:
            metrics['threat_estimator']='known-object-radius finite-body model; radius prior=1.5, self radius=0.5; not uncertainty-robust safety proof'
        elif driver.rule:
            metrics['threat_estimator']='preserved v1 point-observer proxy'
        if driver.gate is not None and request is not None:
            assert driver.internal_request_ms is not None and request>=driver.internal_request_ms
        return dict(arrays=arrays,metrics=metrics,scenario=scenario,config=c,model=model,mapping='uniform_population',
                    controller_state_kind='anatomical_neurons_321' if driver.legacy and driver.legacy.model=='circuit' else 'no_recurrent_neural_state',
                    threshold=self.legacy_rows[model]['threshold'] if model in self.legacy_rows else dict(kind='binary_threat',value=1.,persistence_ms=20),
                    assumptions='known-size prior only for finite variants; rigid billboard/constant relative velocity; no fitting',
                    policy_state_kind='image_history_decoder_and_explicit_gate',
                    known_size_prior=None if not driver.finite else dict(object_radius=self.prior.object_radius,self_radius=self.prior.self_radius,normalized_contact_radius=self.prior.contact_radius))
