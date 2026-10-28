import {it,expect} from 'vitest';
import * as THREE from 'three';
import {roomDesign,roomDimensions,worldToDisplay,displayQuaternion,initialEpisode,observationPhase} from './roomDesign';
import type {Episode,Replay,Sample} from './types';

it('shows exact approved geometry without synthesizing an experiment',()=>{
 expect(roomDimensions(roomDesign.config)).toEqual({center:[0,0,-0],size:[100,100,100]});
 expect(roomDesign.config.room_scene?.static_solids[0].id).toBe('table_volume');
 expect(roomDesign.config.room_scene?.dynamic_solids).toEqual([]);
 expect('metrics' in roomDesign).toBe(false);expect('world' in roomDesign).toBe(false);
});
it('opens archives only on explicit selection, retaining legacy episode links',()=>{
 const episodes=[{id:'legacy'}] as Episode[];
 expect(initialEpisode(episodes,'')).toBeNull();
 expect(initialEpisode(episodes,'?episode=legacy')).toBe('legacy');
 expect(initialEpisode(episodes,'?episode=legacy&view=room')).toBeNull();
 expect(initialEpisode(episodes,'?episode=legacy&live=follow')).toBeNull();
});
it('keeps rendered front, rear and body yaw consistent with scientific coordinates',()=>{
 expect(worldToDisplay([1,2,3])).toEqual([1,3,-2]);
 const world=new THREE.Vector3(0,1,0).applyQuaternion(new THREE.Quaternion(0,0,Math.SQRT1_2,Math.SQRT1_2));
 const display=new THREE.Vector3(0,0,-1).applyQuaternion(displayQuaternion([0,0,Math.SQRT1_2,Math.SQRT1_2]));
 expect(display.distanceTo(new THREE.Vector3(...worldToDisplay(world.toArray())))).toBeLessThan(1e-12);
});
it('shows recovery and normal flight after an earlier escape, preserving collision priority',()=>{
 const data={config:{room_flight:true},metrics:{first_motion_ms:20}} as Replay;
 const sample={gate:'recovery',rule:'clear_under_model'} as Sample;
 expect(observationPhase(null,null,0)).toBe('ROOM DESIGN / NOT RUNNING');
 expect(observationPhase(data,sample,50)).toBe('RECOVERY');
 expect(observationPhase(data,{...sample,gate:'cruise'},100)).toBe('HOVER / CRUISE');
 expect(observationPhase(data,{...sample,rule:'unknown'},100)).toBe('PERCEPTION UNCERTAIN');
 data.metrics.failure={kind:'collision',time_ms:80};
 expect(observationPhase(data,sample,100)).toBe('COLLISION');
});
