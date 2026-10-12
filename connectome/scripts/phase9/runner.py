"""Causal closed-loop orchestration using the actual frozen model APIs."""
import numpy as np
from connectome.scripts.phase4 import dynamics, simulator
from connectome.scripts.phase7.pipeline import FrozenPipeline
from connectome.scripts.phase8.decoder import StreamingDecoder, Threshold
from connectome.scripts.phase8.completion.decoder import CalibratedDecoder
from connectome.scripts.phase8.completion.spatial import assign_fields, frame_drive
from .config import load_config
from .world import World, render_camera


class ClosedLoopRunner:
    def __init__(self,config=None):
        self.config=load_config() if config is None else config
        self.pipeline=FrozenPipeline(); self.decoder=CalibratedDecoder()
        self.body_ids=np.asarray(self.pipeline.encoder.mapping["body_ids"],dtype=np.int64)
        if not np.array_equal(self.body_ids,self.pipeline.circuit.body_ids):
            raise ValueError("Frozen encoder/loader body-ID order differs")
        sim=self.pipeline.simulation_config
        if sim["dt"] != 1 or sim["noise_std"] != 0 or np.any(simulator.build_bias_vector(self.pipeline.circuit,sim) != 0):
            raise ValueError("Streaming adapter requires the unchanged zero-bias/noise 1 ms model")
        self.tau=simulator.build_tau_vector(self.pipeline.circuit,sim)
        self.bias=simulator.build_bias_vector(self.pipeline.circuit,sim)
        self.primary=self.decoder.core.primary_indices
        by_id={int(b):k for k,b in enumerate(self.pipeline.circuit.body_ids)}
        self.steer_indices=[by_id[10228],by_id[10584]]

    def run(self,scenario,*,condition="uniform_population",seed=None):
        c=self.config; world=World(c,scenario)
        if world.done:
            raise ValueError("Neural fixture must start nonterminal; initial overlap is supported/tested by World only")
        if condition == "uniform_population":
            if seed is not None: raise ValueError("Primary uniform input has no synthetic mapping seed")
            mapping=None
        elif condition == c["secondary_condition"]:
            mapping=assign_fields(self.pipeline.encoder.mapping["nodes"],seed)
        else:
            raise ValueError("Unsupported sensory condition")
        sim=self.pipeline.simulation_config
        stream=StreamingDecoder(Threshold(**self.decoder.freeze["models"]["circuit"]["threshold"]),c["duration_ms"])
        frame,diag=render_camera(c,world.fly,world.obstacles,world.radii)
        frames=[frame]; frame_times=[0.0]; rendering=[diag]; processed=0; frame_number=1
        drive=np.zeros(321); states=[np.zeros(321,dtype=np.float64)]
        world_times=[0.0]; fly=[world.fly.copy()]; obstacles=[world.obstacles.copy()]; speeds=[world.speed]
        step_drive=[]; step_indices=[]; scores=[]; outputs=[]; turns=[]; raw_imbalance=[]
        capped=0; activations=0
        while not world.done:
            k=len(outputs)
            if world.time_ms != k or k >= c["duration_ms"]:
                raise ValueError("World/neural clocks diverged")
            available=int(np.searchsorted(np.array(frame_times),k/1000,side="right"))
            if available != processed:
                prefix=np.stack(frames[:available]); timestamps=np.array(frame_times[:available],dtype=np.float64)
                if mapping is None:
                    encoded=self.pipeline.encoder.encode(prefix,timestamps); drive=encoded.drive[-1].copy()
                else:
                    _,spatial,_=frame_drive(self.pipeline.encoder,prefix,timestamps,mapping); drive=spatial[-1].copy()
                processed=available
            x=states[-1]; score=float(x[self.primary].mean()); scores.append(score)
            out=stream.update(float(k),score); outputs.append(out)
            raw=0.0
            if mapping is not None:
                l,r=x[self.steer_indices]/np.array(self.decoder.freeze["steering_normalization"]["gains"])
                if l+r > 0: raw=float((l-r)/(l+r))
            raw_imbalance.append(raw)
            if out["escape_event"]:
                world.request(raw if mapping is not None else 0.0)
            turns.append(world.turn if world.request_ms is not None else 0.0)
            segment=world.step()
            world_times.append(world.time_ms);fly.append(world.fly.copy());obstacles.append(world.obstacles.copy());speeds.append(world.speed)
            # Render exact fractional timestamps from the just-traversed segment.
            # They affect the controller only at a later eligible integer tick.
            while frame_number/c["camera_fps"] <= world.time_ms/1000 and frame_number/c["camera_fps"] < c["duration_ms"]/1000:
                timestamp=frame_number/c["camera_fps"]
                alpha=(timestamp*1000-segment["start_ms"])/(segment["end_ms"]-segment["start_ms"])
                at_fly=segment["fly_start"]+alpha*(segment["fly_end"]-segment["fly_start"])
                at_obs=segment["obstacles_start"]+alpha*(segment["obstacles_end"]-segment["obstacles_start"])
                frame,diag=render_camera(c,at_fly,at_obs,world.radii)
                frames.append(frame);frame_times.append(timestamp);rendering.append(diag);frame_number+=1
            if world.time_ms == k+1:
                scaled=sim["input_scale"]*drive
                preclip=sim["gain"]*(self.pipeline.weights@x)+self.bias+scaled
                capped+=int(np.count_nonzero(preclip > sim["clip_max"])); activations+=321
                next_x=dynamics.euler_step(x,self.pipeline.weights,self.bias,scaled,self.tau,sim["gain"],sim["dt"],sim["clip_max"])
                if not np.all(np.isfinite(next_x)) or np.any(next_x < 0):
                    raise RuntimeError("Invalid neural state; do not omit fixture")
                states.append(next_x);step_drive.append(drive.copy());step_indices.append(available-1)
            elif not world.terminated:
                raise ValueError("Fractional world endpoint without a physical termination")
        states=np.array(states,dtype=np.float64); n=len(outputs)
        offline,steering,action=self.decoder.decode_activity(np.arange(n,dtype=np.float64),states[:n],self.body_ids,c["duration_ms"],
                                                           condition=condition,spatial_mapping=mapping)
        for field in ("sustained_score","eligible","escape_event","escape_requested"):
            np.testing.assert_array_equal(getattr(offline,field),np.array([r[field] for r in outputs]))
        np.testing.assert_array_equal(offline.score,np.array(scores))
        np.testing.assert_array_equal(steering["turn_command"],np.array(turns))
        np.testing.assert_array_equal(steering["raw_dn_imbalance"],np.array(raw_imbalance))
        all_frames=np.stack(frames); timestamps=np.array(frame_times,dtype=np.float64)
        if mapping is None:
            encoded=self.pipeline.encoder.encode(all_frames,timestamps); all_drive=encoded.drive
        else:
            encoded,all_drive,_=frame_drive(self.pipeline.encoder,all_frames,timestamps,mapping)
        input_steps=np.array(step_drive,dtype=np.float64).reshape(-1,321)
        indices=np.array(step_indices,dtype=np.int64)
        np.testing.assert_array_equal(input_steps,all_drive[indices])
        if len(indices):
            np.testing.assert_array_equal(indices,np.searchsorted(timestamps,np.arange(len(indices))/1000,side="right")-1)
        metrics=world.metrics()
        metrics.update(activation_clipped_fraction=capped/activations if activations else 0.0,
                       encoder_valid_fraction=float(np.mean(encoded.diagnostics["valid"])),
                       encoder_cap_fraction=float(np.mean(encoded.channels>=1)),
                       near_or_behind_frame_count=sum(d["near_or_behind"]>0 for d in rendering),
                       direct_dn_input_max=float(all_drive[:,np.array(self.pipeline.encoder.mapping["channel_index"])<0].max()),
                       streamed_offline_decoder_equal=True,causal_prefix_batch_input_equal=True,
                       calibration_scope=c["calibration_scope"],condition=condition,seed=seed)
        action.update(world_calibration_status=c["calibration_scope"],motor_plant=c["protocol_id"],
                      semantics="latched request drives abstract backward/lateral translation after delay; not fly biomechanics")
        arrays=dict(neural_times_ms=np.arange(len(states),dtype=np.float64),states=states,body_ids=self.body_ids.copy(),
                    decision_times_ms=offline.times_ms,score=offline.score,sustained_score=offline.sustained_score,eligible=offline.eligible,
                    escape_event=offline.escape_event,escape_requested=offline.escape_requested,turn_command=steering["turn_command"],
                    raw_dn_imbalance=steering["raw_dn_imbalance"],dn_body_ids=offline.dn_body_ids,dn_activity=offline.dn_activity,
                    world_times_ms=np.array(world_times),fly_position=np.array(fly),obstacle_positions=np.array(obstacles),speed=np.array(speeds),
                    frames=all_frames,frame_timestamps_s=timestamps,frame_drive=all_drive,channels=encoded.channels,
                    frame_valid=encoded.diagnostics["valid"],step_times_ms=np.arange(len(input_steps),dtype=np.float64),
                    step_drive_unscaled=input_steps,step_input_scaled=input_steps*sim["input_scale"],step_frame_indices=indices)
        return dict(arrays=arrays,metrics=metrics,action=action,scenario=world.scenario,config=c,mapping=mapping,
                    calibration_sha256=self.decoder.freeze["payload_sha256"],simulation_config=dict(sim,duration=c["duration_ms"]))
