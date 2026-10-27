"""New neutral-action orchestration around unchanged Phase 9 physical primitives."""
import numpy as np
from connectome.scripts.phase8.decoder import StreamingDecoder, Threshold, decode_score
from connectome.scripts.phase8.completion.spatial import assign_fields, frame_drive
from connectome.scripts.phase9.world import World, render_camera
from .controllers import Controller

class Runner:
    def __init__(self, pipeline, config):
        self.pipeline = pipeline
        self.config = config

    def run(self, scenario, mapping, row, heartbeat=lambda:None):
        c = self.config
        world = World(c, scenario)
        if world.done:
            raise ValueError('Nonterminal existing fixtures required')
        controller = Controller(row['model'], self.pipeline, row.get('net'))
        decoder = StreamingDecoder(Threshold(**row['threshold']), c['duration_ms'])
        spatial = None if mapping == 'uniform_population' else assign_fields(self.pipeline.encoder.mapping['nodes'], int(mapping))
        def encode(frames, times):
            if spatial is None:
                encoded = self.pipeline.encoder.encode(frames, times)
                return encoded, encoded.drive
            encoded, drives, _ = frame_drive(self.pipeline.encoder, frames, times, spatial)
            return encoded, drives
        frame, diag = render_camera(c, world.fly, world.obstacles, world.radii)
        frames, times, rendering = [frame], [0.0], [diag]
        processed = 0
        frame_number = 1
        drive = np.zeros(321, dtype=np.float64)
        states = [controller.state_vector()]
        world_times, flies, obstacles, speeds = [0.0], [world.fly.copy()], [world.obstacles.copy()], [0.0]
        drives, indices, scores, outputs = [], [], [], []
        while not world.done:
            k = len(outputs)
            if k % 100 == 0:
                heartbeat()
            if world.time_ms != k or k >= c['duration_ms']:
                raise ValueError('Clock divergence')
            available = int(np.searchsorted(np.array(times), k/1000, side='right'))
            if available != processed:
                _, all_drive = encode(np.stack(frames[:available]), np.array(times[:available]))
                drive = all_drive[-1].copy()
                processed = available
            score = controller.score(drive)
            out = decoder.update(float(k), score)
            if out['escape_event']:
                if row['model'] == 'no_action':
                    raise ValueError('No-action decoder cannot request')
                world.request(0.0)
            scores.append(score); outputs.append(out); drives.append(drive.copy()); indices.append(available-1)
            segment = world.step()
            world_times.append(world.time_ms); flies.append(world.fly.copy())
            obstacles.append(world.obstacles.copy()); speeds.append(world.speed)
            while frame_number/c['camera_fps'] <= world.time_ms/1000 and frame_number/c['camera_fps'] < c['duration_ms']/1000:
                timestamp = frame_number/c['camera_fps']
                alpha = (timestamp*1000-segment['start_ms'])/(segment['end_ms']-segment['start_ms'])
                at_fly = segment['fly_start']+alpha*(segment['fly_end']-segment['fly_start'])
                at_obs = segment['obstacles_start']+alpha*(segment['obstacles_end']-segment['obstacles_start'])
                frame, diag = render_camera(c, at_fly, at_obs, world.radii)
                frames.append(frame); times.append(timestamp); rendering.append(diag); frame_number += 1
            if world.time_ms == k+1:
                controller.advance(drive)
                states.append(controller.state_vector())
            elif not world.terminated:
                raise ValueError('Fractional endpoint without contact')
        arrays = dict(world_times_ms=np.array(world_times), fly_position=np.array(flies),
                      obstacle_positions=np.array(obstacles), speed=np.array(speeds),
                      frames=np.stack(frames), frame_timestamps_s=np.array(times),
                      decision_times_ms=np.arange(len(scores), dtype=np.float64), score=np.array(scores),
                      decision_drive_unscaled=np.array(drives), decision_input_scaled=.4*np.array(drives),
                      decision_frame_indices=np.array(indices, dtype=np.int64),
                      controller_state_times_ms=np.arange(len(states), dtype=np.float64),
                      controller_states=np.array(states),
                      body_ids=np.asarray(self.pipeline.circuit.body_ids, dtype=np.int64),
                      near_or_behind=np.array([d['near_or_behind'] for d in rendering], dtype=np.int64),
                      projected_objects=np.array([len(d['projected']) for d in rendering], dtype=np.int64))
        for field in ('sustained_score', 'eligible', 'escape_event', 'escape_requested'):
            arrays[field] = np.array([o[field] for o in outputs])
        encoded, all_drive = encode(arrays['frames'], arrays['frame_timestamps_s'])
        arrays.update(frame_valid=encoded.diagnostics['valid'], frame_drive=all_drive,
                      channels=encoded.channels, frame_area_px=encoded.diagnostics['area_px'])
        np.testing.assert_array_equal(arrays['decision_drive_unscaled'], all_drive[arrays['decision_frame_indices']])
        np.testing.assert_array_equal(arrays['decision_frame_indices'],
            np.searchsorted(arrays['frame_timestamps_s'], arrays['decision_times_ms']/1000, side='right')-1)
        offline = decode_score(arrays['decision_times_ms'], arrays['score'], 1000., Threshold(**row['threshold']))
        for field in ('sustained_score', 'eligible', 'escape_event', 'escape_requested'):
            np.testing.assert_array_equal(arrays[field], getattr(offline, field))
        metrics = world.metrics()
        valid = arrays['frame_valid']; time = arrays['frame_timestamps_s']
        pre = np.ones(len(time), dtype=bool) if world.request_ms is None else time <= world.request_ms/1000
        invalid = np.flatnonzero(~valid)
        metrics.update(encoder_valid_fraction=float(valid.mean()), encoder_valid_frames=int(valid.sum()),
            frame_count=len(valid), pre_request_valid_frames=int(valid[pre].sum()),
            pre_request_frame_count=int(pre.sum()), pre_request_valid_fraction=float(valid[pre].mean()),
            first_invalid_frame_ms=None if not len(invalid) else float(time[invalid[0]]*1000),
            encoder_cap_fraction=float(np.mean(encoded.channels>=1)),
            near_or_behind_frame_count=int(np.count_nonzero(arrays['near_or_behind'])),
            activation_clipped_fraction=controller.clipped/(321*controller.updates) if controller.model=='circuit' and controller.updates else None,
            direct_dn_input_max=float(all_drive[:,controller.assigned<0].max()),
            whole_episode_encoder_valid=bool(valid.all()), finite_controller_state=bool(np.isfinite(arrays['controller_states']).all()),
            model=row['id'], mapping=mapping, world_calibration='open_loop_threshold_transfer_no_world_calibration',
            motor_semantics='first-event neutral retreat; unchanged abstract Phase 9 plant')
        return dict(arrays=arrays, metrics=metrics, scenario=scenario, config=c,
                    threshold=row['threshold'], model=row['id'], mapping=mapping,
                    controller_state_kind={'gru':'GRU_hidden_16','circuit':'anatomical_neurons_321',
                                           'feature_only':'stateless','no_action':'stateless'}[row['model']])
