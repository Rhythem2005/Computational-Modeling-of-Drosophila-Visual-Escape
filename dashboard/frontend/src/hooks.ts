import {useCallback,useEffect,useRef,useState} from 'react';
import {get,wsURL} from './api';
import type {Catalog,Graph,LiveFrame,LiveSpec,ProjectStatus,Replay} from './types';
import {liveReplay} from './timeline';
import {initialEpisode} from './roomDesign';

export function useObservatory(){
 const [catalog,setCatalog]=useState<Catalog|null>(null),[graph,setGraph]=useState<Graph|null>(null),[status,setStatus]=useState<ProjectStatus|null>(null),[error,setError]=useState<string|null>(null),[connected,setConnected]=useState(false),[generation,setGeneration]=useState(0);
 const [sessions,setSessions]=useState<LiveSpec[]>([]),[selected,setSelected]=useState<string|null>(null),[liveId,setLiveId]=useState<string|null>(null),[replay,setReplay]=useState<Replay|null>(null),[liveData,setLiveData]=useState<Replay|null>(null),[loading,setLoading]=useState(false),[liveActive,setLiveActive]=useState(false);
 useEffect(()=>{const abort=new AbortController();let stopped=false;let timer:ReturnType<typeof setTimeout>|undefined;let socket:WebSocket|undefined;
  Promise.all([get<Catalog>('/api/v1/catalog',abort.signal),get<Graph>('/api/v1/connectome',abort.signal),get<ProjectStatus>('/api/v1/status',abort.signal)]).then(([c,g,s])=>{if(stopped)return;setCatalog(c);setGraph(g);setStatus(s);setConnected(true);setError(null);setSelected(old=>old&&c.episodes.some(e=>e.id===old)?old:initialEpisode(c.episodes,location.search))}).catch(e=>{if(!stopped){setError(String(e.message));setConnected(false)}});
  function connect(){if(stopped)return;socket=new WebSocket(wsURL('/api/v1/catalog/ws'));socket.onmessage=e=>{const m=JSON.parse(e.data);setConnected(true);if(m.type==='catalog')setCatalog(m.catalog)};socket.onclose=()=>{if(!stopped){setConnected(false);timer=setTimeout(connect,5000)}};socket.onerror=()=>socket?.close()}
  connect();const refresh=()=>get<{sessions:LiveSpec[]}>('/api/v1/live',abort.signal).then(x=>{if(stopped)return;setSessions(x.sessions);if(new URLSearchParams(location.search).get('live')==='follow'){const active=x.sessions.filter(s=>s.active);const newest=active[active.length-1]??x.sessions[x.sessions.length-1];if(newest)setLiveId(newest.id)}}).catch(()=>{});refresh();const poll=setInterval(refresh,1000);
  return()=>{stopped=true;abort.abort();clearInterval(poll);clearTimeout(timer);socket?.close()};
 },[generation]);
 useEffect(()=>{if(!selected)return;const abort=new AbortController();setLoading(true);setError(null);get<Replay>(`/api/v1/episodes/${selected}/replay`,abort.signal).then(data=>{if(!abort.signal.aborted){setReplay(data);setLoading(false);const url=new URL(location.href);url.searchParams.set('episode',selected);history.replaceState(null,'',url)}}).catch(e=>{if(!abort.signal.aborted){setError(e.message);setLoading(false)}});return()=>abort.abort()},[selected,generation]);
 useEffect(()=>{if(!liveId){setLiveData(null);setLiveActive(false);return}let stopped=false;let frames:LiveFrame[]=[];let spec:LiveSpec|null=null;setLiveData(null);setLiveActive(true);const socket=new WebSocket(wsURL(`/api/v1/live/${liveId}/ws`));socket.onmessage=e=>{const message=JSON.parse(e.data);if(stopped)return;if(message.type==='snapshot'){spec=message.session;frames=message.frames;setLiveActive(spec!.active)}if(message.type==='frame')frames=[...frames,message.frame].slice(-200);if(message.type==='ended')setLiveActive(false);if(spec&&(message.type==='snapshot'||message.type==='frame'))setLiveData(liveReplay(spec,frames))};socket.onerror=()=>setLiveActive(false);socket.onclose=()=>!stopped&&setLiveActive(false);return()=>{stopped=true;socket.close()}},[liveId]);
 const select=useCallback((id:string)=>{setLiveId(null);const url=new URL(location.href);url.searchParams.delete('live');url.searchParams.delete('view');history.replaceState(null,'',url);setSelected(id)},[]);
 const showRoom=useCallback(()=>{setSelected(null);setReplay(null);setLiveId(null);setLoading(false);const url=new URL(location.href);url.searchParams.delete('episode');url.searchParams.delete('live');url.searchParams.set('view','room');history.replaceState(null,'',url)},[]);
 return {catalog,graph,status,error,connected,sessions,select,showRoom,selectLive:setLiveId,liveId,liveActive,data:liveId?liveData:replay,loading,retry:()=>setGeneration(g=>g+1)};
}

export function usePlayback(data:Replay|null,live:boolean){
 const [time,setTime]=useState(0),[playing,setPlaying]=useState(false),[rate,setRate]=useState(.1),[loop,setLoop]=useState(false);const timeRef=useRef(0);
 const seek=useCallback((value:number)=>{const next=Math.max(data?.world.times_ms[0]??0,Math.min(data?.duration_ms??0,value));timeRef.current=next;setTime(next)},[data]);
 useEffect(()=>{setPlaying(false);timeRef.current=data?.world.times_ms[0]??0;setTime(timeRef.current)},[data?.episode.id]);
 useEffect(()=>{if(live&&data){timeRef.current=data.duration_ms;setTime(data.duration_ms)}},[live,data]);
 useEffect(()=>{if(!playing||!data||live)return;let last:number|undefined,frame=0;const advance=(now:number)=>{if(last!==undefined){let next=timeRef.current+(now-last)*rate;if(next>=data.duration_ms){if(loop)next=data.world.times_ms[0];else{next=data.duration_ms;setPlaying(false)}}timeRef.current=next;setTime(next)}last=now;frame=requestAnimationFrame(advance)};frame=requestAnimationFrame(advance);return()=>cancelAnimationFrame(frame)},[playing,rate,loop,data,live]);
 const toggle=useCallback(()=>{if(live||!data)return;if(timeRef.current>=data.duration_ms)seek(data.world.times_ms[0]);setPlaying(v=>!v)},[data,live,seek]);
 const step=useCallback((delta:number)=>{setPlaying(false);seek(Math.floor(timeRef.current)+delta)},[seek]);
 return {time,timeRef,playing,rate,setRate,loop,setLoop,seek,toggle,step,pause:()=>setPlaying(false)};
}
