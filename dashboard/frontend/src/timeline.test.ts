// Unexecuted until approval. Only math/clock contracts, not scientific outcomes.
import {describe,it,expect} from 'vitest';
import {heldIndex,number} from './timeline';
describe('causal observation lookup',()=>{
 it('never admits a future camera sample',()=>{const t=[0,1000/60,2000/60];expect(heldIndex(t,16)).toBe(0);expect(heldIndex(t,17)).toBe(1)});
 it('keeps a fractional terminal time inclusive',()=>{expect(heldIndex([0,1,1.25],1.25)).toBe(2)});
 it('does not fabricate an initial sample',()=>{expect(heldIndex([5,10],0)).toBe(-1);expect(heldIndex([],0)).toBe(-1)});
 it('retains the subnormal threshold in display text',()=>{expect(number(5e-324)).toContain('e-324')});
 it('shows missing values explicitly',()=>{expect(number(null)).toBe('—');expect(number(NaN)).toBe('—')});
});

import {liveReplay} from './timeline';
import type {LiveSpec,LiveFrame} from './types';
it('keeps the terminal neural state without inventing a terminal decision or repeated camera frame',()=>{
 const spec:LiveSpec={id:'clock-test',name:'Unit clock contract',protocol:'unit',controller:'unit',source_note:'Unit inputs only',world_config:{fly_radius:.5,duration_ms:1000},active:false};
 const frame=(time_ms:number):LiveFrame=>({time_ms,fly:[0,0],obstacles:[],speed:0,score:1,sustained_score:1,gate_state:null,rule_state:null,encoder_channels:null,encoder_drive:null,encoder_body_ids:[],encoder_valid:null,neural_kind:'unavailable',neural_ids:[],neural_values:[],camera_timestamp_ms:983.333,camera_png_base64:null,events:[]});
 const replay=liveReplay(spec,[frame(990),frame(1000)])!;
 expect(replay.world.times_ms).toEqual([990,1000]);
 expect(replay.decision.times_ms).toEqual([990]);
 expect(replay.camera.count).toBe(1);
});

it('preserves physical altitude and separately held live decision timestamps',()=>{
 const spec:LiveSpec={id:'3d-clock',name:'Unit 3D adapter',protocol:'unit',controller:'unit',source_note:'Unit inputs only',world_config:{fly_radius:.5,world_dimension:3,duration_ms:1000},active:true};
 const frame:LiveFrame={time_ms:30,decision_timestamp_ms:29,neural_timestamp_ms:30,fly:[1,2,3],obstacles:[{id:'unit',position:[4,5,6],radius:1}],speed:0,score:0,sustained_score:0,gate_state:null,rule_state:null,encoder_channels:null,encoder_drive:null,encoder_body_ids:[],encoder_valid:null,neural_kind:'unavailable',neural_ids:[],neural_values:[],camera_timestamp_ms:null,camera_png_base64:null,events:[]};
 const replay=liveReplay(spec,[frame])!;
 expect(replay.world.fly[0]).toEqual([1,2,3]);
 expect(replay.decision.times_ms).toEqual([29]);
});

import {mixQuaternion} from './timeline';
it('interpolates body orientation on the shortest normalized arc',()=>{
 const a:[number,number,number,number]=[0,0,0,1],b:[number,number,number,number]=[0,0,1,0];
 const q=mixQuaternion(a,b,.5);expect(Math.hypot(...q)).toBeCloseTo(1);expect(q[2]).toBeCloseTo(Math.SQRT1_2);
 expect(mixQuaternion(a,[0,0,0,-1],.5)).toEqual(a);
});

it('keeps room body pose and sensor calibration in live observation',()=>{
 const spec:LiveSpec={id:'room-unit',name:'Unit room schema',protocol:'unit',controller:'unit',source_note:'Unit inputs only',world_config:{fly_radius:.5,world_dimension:3,room_flight:true,camera_rig:[{id:'rear',quaternion:[0,0,1,0],width:4,height:4,focal_px:2}]},active:true};
 const frame:LiveFrame={time_ms:0,fly:[0,0,0],fly_quaternion_xyzw:[0,0,1,0],obstacles:[],speed:0,score:null,sustained_score:null,gate_state:'cruise',rule_state:'unknown',encoder_channels:null,encoder_drive:null,encoder_body_ids:[],encoder_valid:null,neural_kind:'unavailable',neural_ids:[],neural_values:[],camera_timestamp_ms:null,camera_png_base64:null,events:[]};
 const r=liveReplay(spec,[frame])!;expect(r.world.quaternion_xyzw?.[0]).toEqual([0,0,1,0]);expect(r.camera.view_ids).toEqual(['rear']);
});
