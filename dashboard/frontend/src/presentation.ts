import type {Episode,Replay,Sample,Node} from './types';
import {label} from './timeline';
const scenes:Record<string,string>={room_front:'Object from the front',room_rear:'Object from behind',room_left:'Object from the left',room_right:'Object from the right',room_above:'Object from above',room_below:'Object from below',room_static:'Stationary object',room_flank_near_miss:'Harmless side pass'};
const controllers:Record<string,string>={ordinary_motion:'Normal flight · baseline',approach_trigger:'Simple approach trigger',surround_avoidance:'Surround avoidance',no_action:'No movement · baseline',planner_only:'Visual planner',circuit_planner:'Circuit + visual planner',gru:'GRU comparison',real:'Anatomical circuit'};
export function sceneName(id:string){const clean=id.replace(/^\d+_/,'').replace(/_(ordinary_motion|approach_trigger|surround_avoidance)$/,'');return scenes[clean]??label(clean)}
export const controllerName=(id:string)=>controllers[id]??label(id);
export function recordingOutcome(e:Episode){
 if(e.failure)return e.failure.kind==='boundary'?'Wall contact':e.failure.kind==='collision'?'Collision':label(e.failure.kind);
 if(e.false_alarm===true)return 'Unnecessary escape';
 if(e.escape_success===true)return 'Escape successful';
 if(e.escape_success===false)return 'Escape criterion not met';
 if(e.false_alarm===false&&e.danger===false)return 'No false alarm';
 return 'Outcome not published';
}
export function neuronValue(n:Node,data:Replay,sample:Sample,signal:'activity'|'input'):number|null{
 const ids=signal==='input'?data.encoder.ids:data.neural.kind==='anatomical'?data.neural.ids:[];
 const values=signal==='input'?sample.drive:sample.neuralValues;const i=ids.indexOf(n.id);
 const v=i>=0?values?.[i]:null;return typeof v==='number'&&Number.isFinite(v)?v:null;
}
export function roleDescription(n:Node){
 if(n.population==='visual_input'&&n.role==='looming_sensor')return 'Visual input · expanding-object sensor in this model.';
 if(n.population==='readout')return n.role==='primary'?'Primary model readout · the main monitored output.':'Secondary model readout · monitored alongside the primary output.';
 return `${label(n.role)} · ${label(n.population)}`;
}
export const isTable=(id:string)=>id==='table_volume';

export function recordingGroup(e:Episode){return e.scenario.startsWith('room_')?'room':e.experiment.includes('multi_')?'multi':'earlier'}
export function experimentName(e:Episode){
 const stamp=e.experiment.match(/(?:room|multi)_(\d{16,20})/);const group=recordingGroup(e);
 if(stamp){const date=new Date(Number(stamp[1])/1e6);if(Number.isFinite(date.getTime()))return `${group==='room'?'Room pilot':'3D multi-object'} · ${new Intl.DateTimeFormat('en-GB',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit',timeZone:'Asia/Kolkata'}).format(date)} IST`}
 return ({phase9:'Original escape study',v2:'Collision study · version 2',v1:'Collision study · version 1'} as Record<string,string>)[e.family]??'Earlier behavior study';
}
