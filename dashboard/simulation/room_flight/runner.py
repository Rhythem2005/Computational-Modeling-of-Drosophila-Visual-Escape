"""Causal surround room loop. No research scenes or model defaults are embedded."""
import time
import numpy as np
from .world import RoomWorld
from .sensors import SurroundRenderer,mosaic
from .perception import SurroundObserver
from .locomotion import RoomBehavior
from .pose import slerp
from .neural_adapter import NullDiagnostic

def envelope_radius(solid):
    return max(np.linalg.norm(p.offset)+(p.radius if p.shape=='sphere' else np.linalg.norm(p.half_extents)) for p in solid.parts)

class RoomRunner:
    def __init__(self,c,model,diagnostic=None):self.c=c;self.model=model;self.diagnostic=diagnostic or NullDiagnostic();self.started=False
    def run(self,scene,observer=None,deadline=None):
        if self.started:raise ValueError('Fresh runner and diagnostic required for independent episode')
        self.started=True;c=self.c;motion=c.motion;world=RoomWorld(c,scene)
        sensor=SurroundRenderer(c);perception=SurroundObserver(c)
        # The declared prior contains static furniture only. Never pass dynamic solids to the policy.
        policy=RoomBehavior(c,self.model,scene.static_solids if c.known_static_map else ())
        observations=[sensor.capture(scene,world.fly,world.quaternion,0.)];processed=0;next_frame=1
        wt=[0.];fly=[world.fly.copy()];quaternions=[world.quaternion.copy()];objects=[world.positions()];speed=[float(np.linalg.norm(world.velocity))];velocities=[world.velocity.copy()]
        neural_outputs=[];states=[];state_times=[];drives=[];channels=[];outputs=[];indices=[];commands=[];events=[];tracking=[];pending_events=[];last_packet=None;first_request=None
        while not world.done:
            k=len(outputs)
            if world.time_ms!=k:raise ValueError('Room decision/world clock divergence')
            if deadline is not None and time.monotonic()>=deadline:raise TimeoutError('Room protocol time budget exhausted')
            new_camera=False
            while processed<len(observations) and observations[processed].time_ms/1000<=k/1000:
                obs=observations[processed];raw,reasons=perception.observe(obs);self.diagnostic.observe(obs);processed+=1;new_camera=True
                tracking.append(dict(time_ms=obs.time_ms,reasons=list(reasons),tracks=[dict(id=x['id'],motion_valid=x['motion_valid'],position_estimate=x['position'].tolist(),velocity_estimate=None if x['velocity'] is None else x['velocity'].tolist(),range_interval=x['range_interval'],views=x['views'],reasons=x['reasons']) for x in raw]))
            tracks,fresh=perception.tracks(k,world.fly,world.velocity)
            neural=self.diagnostic.sample(k);neural_outputs.append(neural);states.append(neural['state']);state_times.append(float(k));drives.append(neural['drive']);channels.append(neural['channels']);indices.append(processed-1)
            decision=policy.update(k,tracks,fresh,perception.last_reasons,world.fly.copy(),world.velocity.copy(),world.quaternion.copy(),world.target.copy(),[(t,v.copy()) for t,v in world.pending],new_camera)
            if decision.initiation:
                if first_request is None:first_request=float(k)
                event=dict(time_ms=float(k),kind='request',label=f'{self.model} bout {policy.bouts}');events.append(event);pending_events.append(event)
            if decision.target is not None:
                world.request(decision.target);commands.append(dict(time_ms=float(k),target=decision.target.tolist(),source=decision.source,bout=policy.bouts))
            outputs.append(dict(score=neural['score'],sustained_score=neural['sustained_score'],escape_event=decision.initiation,escape_requested=first_request is not None,gate_state=decision.mode,rule_state=decision.rule,perception_unknown=decision.unknown,command_source=decision.source,planner_feasible=-1 if decision.feasible is None else int(decision.feasible)))
            if observer is not None and (new_camera or decision.initiation):
                obs=observations[processed-1]
                packet=dict(time_ms=float(k),decision_timestamp_ms=float(k),neural_timestamp_ms=float(k) if len(neural['state']) else None,fly=world.fly.tolist(),fly_quaternion_xyzw=world.quaternion.tolist(),obstacles=[dict(id=s.id,position=p.tolist(),radius=float(envelope_radius(s)),parts=[v.public() for v in s.parts]) for s,p in zip(scene.dynamic_solids,world.positions())],speed=float(np.linalg.norm(world.velocity)),score=neural['score'],sustained_score=neural['sustained_score'],gate_state=decision.mode,rule_state=decision.rule,neural_kind='anatomical' if len(neural['state'])==321 else 'unavailable',neural_ids=self.diagnostic.ids.tolist(),neural_values=neural['state'].tolist(),encoder_channels=neural['channels'].tolist() if len(neural['channels']) else None,encoder_drive=neural['drive'].tolist() if len(neural['drive']) else None,encoder_body_ids=self.diagnostic.ids.tolist() if len(neural['drive']) else [],encoder_valid=False if len(neural['state']) else None,camera_timestamp_ms=obs.time_ms,camera_frame=mosaic(obs),sensor_frames=[dict(id=v.id,time_ms=obs.time_ms,quaternion_xyzw=list(v.quaternion),image=image) for v,image in zip(obs.views,obs.images)],events=list(pending_events));pending_events=[];last_packet=packet;observer.publish(packet)
            segment=world.step();wt.append(world.time_ms);fly.append(world.fly.copy());quaternions.append(world.quaternion.copy());objects.append(world.positions());speed.append(float(np.linalg.norm(world.velocity)));velocities.append(world.velocity.copy())
            if world.first_motion_ms is not None and not any(e['kind']=='motion' for e in events):
                event=dict(time_ms=world.time_ms,kind='motion',label='First observed displacement');events.append(event);pending_events.append(event)
            while next_frame/motion.camera_fps<=world.time_ms/1000 and next_frame/motion.camera_fps<motion.duration_ms/1000:
                stamp=(next_frame/motion.camera_fps)*1000;alpha=(stamp-segment['start_ms'])/(segment['end_ms']-segment['start_ms'])
                observations.append(sensor.capture(scene,segment['fly_start']+alpha*(segment['fly_end']-segment['fly_start']),slerp(segment['q_start'],segment['q_end'],alpha),stamp));next_frame+=1
            if world.time_ms==k+1:self.diagnostic.advance()
        if world.time_ms==len(outputs):states.append(self.diagnostic.state_vector());state_times.append(world.time_ms)
        if world.failure:
            event=dict(time_ms=world.time_ms,kind=world.failure['kind'],label=world.failure['kind'].title());events.append(event);pending_events.append(event)
        if observer is not None and last_packet is not None:
            observer.publish(dict(last_packet,time_ms=world.time_ms,decision_timestamp_ms=float(len(outputs)-1),neural_timestamp_ms=state_times[-1] if len(states[-1]) else None,fly=world.fly.tolist(),fly_quaternion_xyzw=world.quaternion.tolist(),neural_values=states[-1].tolist(),score=outputs[-1]['score'],sustained_score=outputs[-1]['sustained_score'],gate_state=outputs[-1]['gate_state'],rule_state=outputs[-1]['rule_state'],speed=float(np.linalg.norm(world.velocity)),obstacles=[dict(id=s.id,position=p.tolist(),radius=float(envelope_radius(s)),parts=[v.public() for v in s.parts]) for s,p in zip(scene.dynamic_solids,world.positions())],events=list(pending_events)))
        frame_channels,frame_drive=self.diagnostic.frame_record(observations)
        frame_times=np.array([o.time_ms/1000 for o in observations]);arrays=dict(world_times_ms=np.array(wt),fly_position=np.array(fly),fly_quaternion_xyzw=np.array(quaternions),fly_velocity=np.array(velocities),obstacle_positions=np.array(objects),speed=np.array(speed),frames=np.stack([mosaic(o) for o in observations]),sensor_frames=np.array([o.images for o in observations]),frame_timestamps_s=frame_times,decision_times_ms=np.arange(len(outputs),dtype=float),controller_states=np.array(states),controller_state_times_ms=np.array(state_times),body_ids=self.diagnostic.ids.copy(),decision_drive_unscaled=np.array(drives),frame_drive=frame_drive,channels=frame_channels,decision_frame_indices=np.array(indices),frame_valid=np.zeros(len(observations),dtype=bool),frame_frozen_domain_valid=np.zeros(len(observations),dtype=bool))
        # Additional diagnostic evidence is saved on the decision clock, separately
        # from policy escape_event/commands. No neural motor claim is implied.
        if neural_outputs and 'dn_body_ids' in neural_outputs[0]:
            arrays['dn_body_ids']=neural_outputs[0]['dn_body_ids'].copy()
            for key in ('dn_activity','dn_recurrent_input','motor_mapping_available'):
                arrays[key]=np.asarray([n[key] for n in neural_outputs])
        for key in outputs[0]:
            values=[o[key] for o in outputs];arrays[key]=np.array([np.nan if v is None else v for v in values]) if key in ('score','sustained_score') else np.array(values)
        config=c.public();config.update(room_scene=scene.public(),neural_role=self.diagnostic.role)
        scenario=dict(scenario_id=scene.scenario_id,fly_position=scene.fly_position,fly_quaternion_xyzw=scene.fly_quaternion,obstacles=[dict(id=s.id,position=s.position(0).tolist(),radius=float(envelope_radius(s)),parts=[p.public() for p in s.parts]) for s in scene.dynamic_solids])
        from .recording import metrics
        result=metrics(c,scene,arrays,world.failure,commands)
        result.update(first_request_ms=first_request,first_motion_ms=world.first_motion_ms,scheduled_actuation_ms=None if first_request is None else first_request+motion.actuation_delay_ms,avoidance_bouts=policy.bouts,unknown_ticks=sum(v['perception_unknown'] for v in outputs))
        supported=sum(bool(t['tracks']) and not t['reasons'] and all(x['motion_valid'] for x in t['tracks']) for t in tracking)
        no_target=sum(not t['tracks'] and t['reasons']==['no_target_visible_not_clearance_proof'] for t in tracking)
        result['sensory_support']=dict(captured_synchronized_frames=len(observations),processed_tracking_frames=len(tracking),fully_motion_supported_frames=supported,no_visible_target_frames=no_target,uncertain_tracking_frames=len(tracking)-supported-no_target,fully_motion_supported_fraction=supported/len(tracking),unknown_policy_tick_fraction=result['unknown_ticks']/len(outputs),per_view_captured_frames={v.id:len(observations) for v in c.views},scope='Support under declared color/size/pose priors; no visible target is not certified clearance; frozen encoder domain remains unsupported')
        return dict(arrays=arrays,config=config,scenario=scenario,canonical_scene=scene.public(),model=self.model,metrics=result,commands=commands,events=events,tracking=tracking,threshold=self.diagnostic.threshold,policy_attribution='Conventional surround visual controller; anatomical activity is optional front-view diagnostic only',assumptions='Artificial surround coverage, color and known-size priors, ideal proprioception, declared static map, yaw kinematics; not biological free flight')
