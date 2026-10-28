import {it,expect} from 'vitest';
import {sceneName,controllerName,recordingOutcome,neuronValue,isTable,roleDescription} from './presentation';
import type {Episode,Replay,Sample,Node} from './types';
const episode={failure:null,danger:null,false_alarm:null,escape_success:null} as Episode;
it('never converts an unpublished outcome to successful or silent',()=>{
 expect(recordingOutcome(episode)).toBe('Outcome not published');
 expect(recordingOutcome({...episode,failure:{kind:'boundary',time_ms:5}})).toBe('Wall contact');
 expect(recordingOutcome({...episode,false_alarm:true})).toBe('Unnecessary escape');
});
it('makes room and live worker identifiers understandable without changing their IDs',()=>{
 expect(sceneName('05_room_rear_surround_avoidance')).toBe('Object from behind');
 expect(sceneName('room_flank_near_miss')).toBe('Harmless side pass');
 expect(controllerName('ordinary_motion')).toContain('baseline');
});
it('matches neuron signals by recorded ID, retains zero and rejects nonfinite or missing values',()=>{
 const node={id:12,type:'LC4',role:'looming_sensor',population:'visual_input'} as Node;
 const data={neural:{kind:'anatomical',ids:[13,12]},encoder:{ids:[12,13]}} as unknown as Replay;
 const sample={neuralValues:[.8,0],drive:[.4,.5]} as Sample;
 expect(neuronValue(node,data,sample,'activity')).toBe(0);
 expect(neuronValue(node,data,sample,'input')).toBe(.4);
 expect(neuronValue({...node,id:99},data,sample,'activity')).toBeNull();
 expect(neuronValue(node,data,{...sample,drive:[NaN]},'input')).toBeNull();
 expect(roleDescription(node)).toContain('Visual input');
});
it('does not mistake GRU hidden states for individual anatomical neurons',()=>{
 const data={neural:{kind:'gru_hidden',ids:[12]},encoder:{ids:[]}} as unknown as Replay;
 expect(neuronValue({id:12} as Node,data,{neuralValues:[.7]} as Sample,'activity')).toBeNull();
});
it('hides only the requested table, preserving other recorded static geometry',()=>{
 expect(isTable('table_volume')).toBe(true);expect(isTable('wall')).toBe(false);
});
