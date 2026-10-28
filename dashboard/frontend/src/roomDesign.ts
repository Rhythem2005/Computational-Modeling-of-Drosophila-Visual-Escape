import * as THREE from 'three';
import protocol from '../../simulation/room_flight/proposals/initial_directional/protocol.json';
import type {Position,Quaternion,RoomSolid,WorldConfig,RigView,Episode,Sample,Replay,Vec2} from './types';

// Geometry only, imported from the exact reviewed manifest. No synthetic replay,
// camera pixels, neural signals, motion or performance results are generated.
const initial=protocol.scenes[0];
export const roomDesign={
 protocol:protocol.protocol_id,
 config:{...protocol.settings.motion,bounds:protocol.settings.motion.bounds as Vec2[],room_flight:true,world_dimension:3,
  room_color:protocol.settings.room_color,camera_rig:protocol.settings.views as RigView[],
  room_scene:{static_solids:initial.static_solids as RoomSolid[],dynamic_solids:[]}} as WorldConfig,
 fly:initial.fly_position as [number,number,number],
 quaternion:initial.fly_quaternion as Quaternion,
};
export const worldToDisplay=(p:Position,height=0):[number,number,number]=>[p[0],(p.length===3?p[2]:0)+height,-p[1]];
const frame=new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1,0,0),-Math.PI/2);
export function displayQuaternion(value?:Quaternion){return frame.clone().multiply(new THREE.Quaternion(...(value??[0,0,0,1]))).multiply(frame.clone().invert())}

export function roomDimensions(config:WorldConfig){
 const b=config.bounds!;
 return {center:worldToDisplay(b.map(pair=>(pair[0]+pair[1])/2) as [number,number,number]),
  size:[b[0][1]-b[0][0],b[2][1]-b[2][0],b[1][1]-b[1][0]] as [number,number,number]};
}
export function initialEpisode(episodes:Episode[],search:string){
 const q=new URLSearchParams(search);if(q.get('view')==='room'||q.has('live'))return null;
 const id=q.get('episode');return episodes.some(e=>e.id===id)?id:null;
}
export function observationPhase(data:Replay|null,sample:Sample|null,time:number){
 if(!data||!sample)return 'ROOM DESIGN / NOT RUNNING';
 if(data.metrics.failure&&time>=data.metrics.failure.time_ms)return data.metrics.failure.kind.toUpperCase();
 if(data.config.room_flight){
  const phases:Record<string,string>={cruise:'HOVER / CRUISE',active:'ACTIVE AVOIDANCE',recovery:'RECOVERY',infeasible:'NO FEASIBLE ROUTE'};
  return sample.rule==='unknown'?'PERCEPTION UNCERTAIN':phases[sample.gate]??'OBSERVING';
 }
 const m=data.metrics;
 if(typeof m.first_motion_ms==='number'&&time>=m.first_motion_ms)return 'ESCAPE IN MOTION';
 if(typeof m.first_request_ms==='number'&&time>=m.first_request_ms)return 'ACTUATION DELAY';
 if(sample.gate==='retired_clear')return 'REQUEST RETIRED';
 return sample.rule==='threat'?'THREAT EVIDENCE':'OBSERVING';
}
