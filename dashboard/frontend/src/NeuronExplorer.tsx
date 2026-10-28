import {useMemo,useState} from 'react';
import {Search,X} from 'lucide-react';
import type {Graph,Replay,Sample,Node} from './types';
import {number,label} from './timeline';
import {neuronValue,roleDescription} from './presentation';

export function NeuronExplorer({graph,data,sample,selected,select,signal,setSignal,close}:{graph:Graph|null;data:Replay|null;sample:Sample|null;selected:Node|null;select:(n:Node)=>void;signal:'activity'|'input';setSignal:(v:'activity'|'input')=>void;close:()=>void}){
 const [query,setQuery]=useState(''),[population,setPopulation]=useState('all'),[order,setOrder]=useState('id');
 const types=useMemo(()=>[...new Set(graph?.nodes.map(n=>n.type)??[])],[graph]);
 const nodes=useMemo(()=>{const rows=graph?.nodes.filter(n=>(population==='all'||n.type===population)&&`${n.type} ${n.id} ${n.side} ${n.role}`.toLowerCase().includes(query.toLowerCase()))??[];return rows.sort((a,b)=>order==='signal'&&data&&sample?((neuronValue(b,data,sample,signal)??-Infinity)-(neuronValue(a,data,sample,signal)??-Infinity))||a.id-b.id:a.id-b.id)},[graph,population,query,order,data,sample,signal]);
 const value=(n:Node)=>data&&sample?neuronValue(n,data,sample,signal):null;
 const connections=useMemo(()=>graph&&selected?graph.edges.filter(e=>e.source===selected.id||e.target===selected.id).sort((a,b)=>b.weight-a.weight):[],[graph,selected]);
 return <section className="glass neuron-explorer" aria-label="Neuron explorer">
  <div className="panel-heading"><div><span className="eyebrow mint">NEURON EXPLORER</span><h2>Inside the circuit</h2></div><button className="icon-button" onClick={close} aria-label="Close neuron explorer"><X size={17}/></button></div>
  <p className="neuron-context">{!data?'Open a recording or connect a live source to inspect synchronized signals.':data.config.room_flight?'Front-view diagnostic · uncalibrated room domain · does not control room escapes.':data?.neural.kind==='gru_hidden'?'GRU states are not anatomical neurons. The graph shows structure only.':'Recorded circuit signals, synchronized with the simulation clock.'}</p>
  <div className="neuron-signal" aria-label="Neural signal"><button aria-pressed={signal==='activity'} onClick={()=>setSignal('activity')}>Activity</button><button aria-pressed={signal==='input'} onClick={()=>setSignal('input')}>Input drive</button><span>{number(signal==='activity'?sample?.neuralTime:data&&sample?data.encoder.times_ms[sample.encoderIndex]:null,1)} ms</span></div>
  <label className="neuron-search"><Search size={14}/><input aria-label="Find a neuron" placeholder="Search type, role or neuron ID" value={query} onChange={e=>setQuery(e.target.value)}/></label>
  <label className="neuron-filter">Population<select value={population} onChange={e=>setPopulation(e.target.value)}><option value="all">All populations</option>{types.map(t=><option key={t}>{t}</option>)}</select></label>
  <label className="neuron-filter">Order<select value={order} onChange={e=>setOrder(e.target.value)}><option value="id">Neuron ID</option><option value="signal">Highest current signal</option></select></label>
  <div className="neuron-columns"><span>{nodes.length} neurons</span><span>{signal==='activity'?'Activity':'Input drive'} · raw value</span></div>
  <div className="neuron-list">{nodes.map(n=><button key={n.id} aria-pressed={selected?.id===n.id} onClick={()=>select(n)}><span><b>{n.type}</b><small>{label(n.side)} · {n.id}</small></span><span>{number(value(n),5)}</span></button>)}{!nodes.length&&<p className="neuron-context">{graph?'No matching neurons.':'Connectivity is available when the data service is connected.'}</p>}</div>
  {selected?<div className="neuron-detail"><span className="eyebrow">{selected.type} · {label(selected.side)}</span><p>{roleDescription(selected)}</p><dl><div><dt>Neuron ID</dt><dd>{selected.id}</dd></div><div><dt>Activity</dt><dd>{data&&sample?number(neuronValue(selected,data,sample,'activity'),5):'—'}</dd></div><div><dt>Input drive</dt><dd>{data&&sample?number(neuronValue(selected,data,sample,'input'),5):'—'}</dd></div></dl><details><summary>Strongest structural connections ({connections.length})</summary>{connections.slice(0,8).map(e=><button key={`${e.source}-${e.target}`} onClick={()=>{const n=graph?.nodes.find(n=>n.id===(e.source===selected.id?e.target:e.source));if(n)select(n)}}>{e.source===selected.id?'To':'From'} {e.source===selected.id?e.target:e.source}<span>{e.weight} synapses</span></button>)}{!connections.length&&<p>No recorded connections.</p>}</details></div>:<p className="neuron-context">Select a neuron here or in the 3D circuit to inspect its role and connections.</p>}
  <p className="neuron-legend">— = unavailable · brighter nodes = higher positive signal within the current frame. Positions are schematic; connectivity does not prove a causal role in an escape.</p>
 </section>;
}
