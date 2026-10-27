"""Causal 1-ms orchestration. This new engineering experiment never replaces Phase 9."""
from dataclasses import asdict
import math,time
import numpy as np
from .world import World,render_camera
from .perception import VisualTracker
from .controller import AvoidanceController

class Runner:
    def __init__(self,c,model,circuit):self.c=c;self.model=model;self.circuit=circuit
    def run(self,scenario,observer=None,deadline=None):
        if getattr(self.circuit,'_episode_started',False):raise ValueError('A fresh reset circuit is required for each independent episode')
        self.circuit._episode_started=True
        c=self.c;world=World(c,scenario);tracker=VisualTracker(c);policy=AvoidanceController(c,self.model)
        frames=[];frame_times=[];camera_records=[];next_frame=0;tracks=[];reasons=['no_history']
        world_times=[0.];flies=[world.fly.copy()];objects=[world.obstacles.copy()];speeds=[float(np.linalg.norm(world.velocity))]
        states=[];outputs=[];drives=[];frame_indices=[];tracking=[];commands=[];events=[];queue_events=[]
        first_internal=None;first_request=None;last_packet=None
        def observe_camera(fly,obstacles,stamp):
            nonlocal tracks,reasons
            frame,diag=render_camera(c,fly,obstacles,world.radii)
            frames.append(frame);frame_times.append(stamp);camera_records.append(diag)
        observe_camera(world.fly,world.obstacles,0.);next_frame=1;processed=0
        while not world.done:
            k=len(outputs)
            if world.time_ms!=k:raise ValueError('World/controller clock divergence')
            if deadline is not None and time.monotonic()>deadline:raise TimeoutError('Stage time budget exhausted')
            new_camera=False
            while processed<len(frames) and frame_times[processed]/1000<=k/1000:
                tracks,reasons=tracker.observe(frames[processed],frame_times[processed]);self.circuit.observe(frames[processed],frame_times[processed]);processed+=1;new_camera=True
            state=self.circuit.sample(k);states.append(state['state']);drives.append(state['drive']);frame_indices.append(processed-1)
            if state['escape_event'] and first_internal is None:
                first_internal=float(k);e=dict(time_ms=float(k),kind='internal',label='Frozen circuit initiation');events.append(e);queue_events.append(e)
            _,fresh=tracker.current(k)
            decision=policy.update(k,tracks,fresh,reasons,bool(state['escape_requested']),world.fly.copy(),world.velocity.copy(),world.target.copy(),[(t,v.copy()) for t,v in world.pending],new_camera)
            if decision.request:
                if first_request is None:first_request=float(k)
                e=dict(time_ms=float(k),kind='request',label=f'Avoidance bout {policy.bouts} initiated');events.append(e);queue_events.append(e)
            if decision.target is not None:world.request(decision.target);commands.append(dict(time_ms=float(k),target=decision.target.tolist(),bout=policy.bouts))
            out=dict(score=state['score'],sustained_score=state['sustained_score'],escape_event=decision.request,escape_requested=first_request is not None,
                rule_state=decision.rule,gate_state=decision.phase,track_count=decision.track_count,perception_unknown=decision.unknown,
                planner_feasible=decision.feasible,bout=policy.bouts)
            outputs.append(out)
            tracking.append(dict(time_ms=k,reasons=list(reasons),tracks=[dict(id=t.identity,time_ms=t.time_ms,relative_position=t.relative_position.tolist(),relative_velocity=None if t.relative_velocity is None else t.relative_velocity.tolist(),motion_valid=t.motion_valid,reasons=t.reasons) for t in tracks]))
            if observer is not None and (new_camera or decision.request):
                enc=self.circuit.encoded
                last_packet=dict(time_ms=float(k),decision_timestamp_ms=float(k),neural_timestamp_ms=float(k),fly=world.fly.tolist(),obstacles=[dict(id=o['id'],position=p.tolist(),radius=float(r)) for o,p,r in zip(scenario.obstacles,world.obstacles,world.radii)],speed=float(np.linalg.norm(world.velocity)),score=state['score'],sustained_score=state['sustained_score'],gate_state=decision.phase,rule_state=decision.rule,encoder_channels=enc.channels[-1].tolist(),encoder_drive=state['drive'].tolist(),encoder_body_ids=self.circuit.ids.tolist(),encoder_valid=bool(enc.diagnostics['valid'][-1]) and len(tracks)==1 and not reasons,neural_kind='anatomical',neural_ids=self.circuit.ids.tolist(),neural_values=state['state'].tolist(),camera_timestamp_ms=frame_times[processed-1],camera_frame=frames[processed-1].copy(),events=list(queue_events));observer.publish(last_packet);queue_events=[]
            segment=world.step();world_times.append(world.time_ms);flies.append(world.fly.copy());objects.append(world.obstacles.copy());speeds.append(float(np.linalg.norm(world.velocity)))
            if world.first_motion_ms is not None and not any(e['kind']=='motion' for e in events):
                e=dict(time_ms=world.time_ms,kind='motion',label='First observed displacement');events.append(e);queue_events.append(e)
            while next_frame/c.camera_fps<=world.time_ms/1000 and next_frame/c.camera_fps<c.duration_ms/1000:
                stamp=(next_frame/c.camera_fps)*1000;alpha=(stamp-segment['start_ms'])/(segment['end_ms']-segment['start_ms'])
                observe_camera(segment['fly_start']+alpha*(segment['fly_end']-segment['fly_start']),segment['obstacles_start']+alpha*(segment['obstacles_end']-segment['obstacles_start']),stamp);next_frame+=1
            if world.time_ms==k+1:self.circuit.advance()
        # Final physical and neural states have their own clocks; never create a terminal decision.
        state_times=np.arange(len(states),dtype=float)
        if world.time_ms==len(outputs):states.append(self.circuit.controller.state_vector());state_times=np.arange(len(states),dtype=float)
        encoded=self.circuit.pipeline.encoder.encode(np.stack(frames),np.asarray(frame_times,dtype=float)/1000)
        diagnostic_tracker=VisualTracker(c);perception_valid=[];domain_valid=[]
        for image,stamp in zip(frames,frame_times):
            observed,why=diagnostic_tracker.observe(image,stamp)
            perception_valid.append(bool(observed) and not why and all(t.motion_valid for t in observed))
            domain_valid.append(len(observed)==1 and not why)
        arrays=dict(frame_perception_valid=np.array(perception_valid),frame_frozen_domain_valid=np.array(domain_valid),world_times_ms=np.array(world_times),fly_position=np.array(flies),obstacle_positions=np.array(objects),speed=np.array(speeds),
                    frames=np.stack(frames),frame_timestamps_s=np.asarray(frame_times)/1000,decision_times_ms=np.arange(len(outputs),dtype=float),
                    controller_states=np.array(states),controller_state_times_ms=state_times,body_ids=self.circuit.ids,
                    decision_drive_unscaled=np.array(drives),decision_frame_indices=np.array(frame_indices),channels=encoded.channels,
                    frame_drive=encoded.drive,frame_valid=encoded.diagnostics['valid'],world_dimension=np.array(c.dimensions))
        for key in outputs[0]:arrays[key]=np.array([o[key] for o in outputs],dtype=object if key=='planner_feasible' else None)
        # Object dtype is never persisted: nullable feasibility gets an explicit int sentinel.
        arrays['planner_feasible']=np.array([-1 if o['planner_feasible'] is None else int(o['planner_feasible']) for o in outputs],dtype=np.int8)
        from .recording import calculate_metrics
        metrics=calculate_metrics(c,scenario,arrays,world.failure,commands)
        metrics.update(perception_valid_fraction=float(np.mean(perception_valid)),frozen_encoder_valid_fraction=float(encoded.diagnostics['valid'].mean()),frozen_domain_valid_fraction=float(np.mean(np.array(domain_valid)&encoded.diagnostics['valid'])),model=self.model,internal_request_ms=first_internal,first_request_ms=first_request,
            scheduled_actuation_ms=None if first_request is None else first_request+c.actuation_delay_ms,
            first_motion_ms=world.first_motion_ms,avoidance_bouts=policy.bouts,unknown_ticks=sum(o['perception_unknown'] for o in outputs),
            unsupported_frozen_encoder_multiobject_ticks=sum(o['track_count']!=1 for o in outputs),
            domain='new_multi_object_engineering_not_independently_validated')
        if world.failure:
            e=dict(time_ms=world.time_ms,kind=world.failure['kind'],label=world.failure['kind'].title());events.append(e);queue_events.append(e)
        if observer is not None and last_packet is not None:
            final_packet=dict(last_packet,time_ms=world.time_ms,decision_timestamp_ms=float(len(outputs)-1),neural_timestamp_ms=float(state_times[-1]),fly=world.fly.tolist(),speed=float(np.linalg.norm(world.velocity)),neural_values=arrays['controller_states'][-1].tolist(),score=outputs[-1]['score'],sustained_score=outputs[-1]['sustained_score'],gate_state=outputs[-1]['gate_state'],rule_state=outputs[-1]['rule_state'],events=list(queue_events),obstacles=[dict(id=o['id'],position=p.tolist(),radius=float(r)) for o,p,r in zip(scenario.obstacles,world.obstacles,world.radii)])
            observer.publish(final_packet)
        return dict(arrays=arrays,config=c.public(),scenario=asdict(scenario),model=self.model,metrics=metrics,
            tracking=tracking,commands=commands,events=events,threshold=self.circuit.freeze['threshold'],
            assumptions='Known common object radius; constant-velocity visual prediction; stabilized billboard camera; kinematic 3-D motion, not biological flight',
            policy_attribution='Frozen anatomical initiation plus separate engineering planner' if self.model=='circuit_planner' else self.model)
