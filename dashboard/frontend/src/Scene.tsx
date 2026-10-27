import {Component,Suspense,useEffect,useMemo,useRef} from 'react';
import type {ComponentRef,ErrorInfo,ReactNode} from 'react';
import {Canvas,useFrame,useThree} from '@react-three/fiber';
import {Grid,Html,Line,OrbitControls} from '@react-three/drei';
import * as THREE from 'three';
import type {Graph,Node,Replay,Sample,Position} from './types';
import {label,number} from './timeline';

export type CameraMode='overview'|'follow'|'top'|'circuit';
export type Inspection={kind:'fly'|'obstacle'|'neuron';index?:number;node?:Node}|null;
const COLORS:Record<string,string>={LC4:'#80d5d3',LPLC2:'#a6f1b3',DNp01:'#ffc07a',DNp02:'#cdb1ff',DNp04:'#cdb1ff',DNp06:'#f69ba6',DNp11:'#f69ba6'};
const xyz=(p:Position,height=0):[number,number,number]=>[p[0],(p.length===3?p[2]:0)+height,-p[1]];

class SceneBoundary extends Component<{children:ReactNode},{failed:boolean}>{
 state={failed:false};static getDerivedStateFromError(){return {failed:true}}
 componentDidCatch(error:Error,info:ErrorInfo){console.error('3D observation layer unavailable',error,info.componentStack)}
 render(){return this.state.failed?<div className="canvas-fallback"><span>3D VIEW UNAVAILABLE</span><p>WebGL could not initialize. The recorded data, camera feed and timeline remain available.</p></div>:this.props.children}
}

function CameraRig({mode,sample,reset}:{mode:CameraMode;sample:Sample|null;reset:number}){
 const controls=useRef<ComponentRef<typeof OrbitControls>|null>(null);const {camera}=useThree();
 useEffect(()=>{if(!controls.current)return;camera.up.set(0,1,0);if(mode==='top'){camera.position.set(0,49,1);controls.current.target.set(0,0,-3)}else if(mode==='circuit'){camera.position.set(29,14,17);controls.current.target.set(15,7,0)}else{camera.position.set(27,22,34);controls.current.target.set(0,0,-4)}controls.current.update()},[mode,reset,camera]);
 useFrame((_,delta)=>{if(mode==='follow'&&sample&&controls.current){const p=new THREE.Vector3(...xyz(sample.fly));controls.current.target.lerp(p,Math.min(1,delta*5));camera.position.lerp(p.clone().add(new THREE.Vector3(9,7,12)),Math.min(1,delta*2));controls.current.update()}});
 return <OrbitControls ref={controls} makeDefault enableDamping dampingFactor={.08} minDistance={3} maxDistance={130} maxPolarAngle={Math.PI*.84} enablePan={mode!=='follow'} enableRotate={mode!=='follow'}/>;
}

function Arena({data}:{data:Replay|null}){
 const offset=data?.config.world_dimension===3&&data.config.bounds?.[2]?data.config.bounds[2][0]+1.84:0;
 return <group position={[0,offset,0]}>
  <mesh rotation={[-Math.PI/2,0,0]} position={[0,-1.84,0]}><planeGeometry args={[220,220]}/><meshStandardMaterial color="#071415" roughness={.94} metalness={.15}/></mesh>
  <Grid position={[0,-1.8,0]} args={[120,120]} cellSize={2} sectionSize={10} cellThickness={.45} sectionThickness={.8} cellColor="#16413d" sectionColor="#2c6256" fadeDistance={80} fadeStrength={1.7} infiniteGrid/>
  {[5,10,20].map(r=><mesh key={r} rotation={[-Math.PI/2,0,0]} position={[0,-1.77,0]}><ringGeometry args={[r-.012,r,128]}/><meshBasicMaterial color="#6caa8b" transparent opacity={.18}/></mesh>)}
  <Line points={[[-35,-1.75,0],[35,-1.75,0]]} color="#549f82" transparent opacity={.18}/>
  <Line points={[[0,-1.75,-40],[0,-1.75,35]]} color="#549f82" transparent opacity={.18}/>
  <Html position={[0,-1.7,-22]} center distanceFactor={35}><span className="world-coordinate">+Y / APPROACH CORRIDOR</span></Html>
 </group>;
}

function FruitFly({data,sample,inspect}:{data:Replay;sample:Sample;inspect:(v:Inspection)=>void}){
 const collision=data.metrics.failure?.kind==='collision'&&sample.worldIndex===data.world.times_ms.length-1;
 const color=collision?'#ff7c6c':'#b9f6cd';
 const legs=useMemo(()=>[-1,1].flatMap(side=>[-.12,.08,.28].map((z,i)=>[[side*.15,-.08,z],[side*(.35+i*.04),-.3,z+.12],[side*.49,-.4,z+.24]] as [number,number,number][])),[]);
 return <group position={xyz(sample.fly)} onClick={e=>{e.stopPropagation();inspect({kind:'fly'})}}>
  <group scale={[.23,.21,.42]} position={[0,0,.13]}><mesh><sphereGeometry args={[1,24,16]}/><meshStandardMaterial color="#496852" metalness={.65} roughness={.3}/></mesh></group>
  <mesh position={[0,.04,-.28]} scale={[.22,.2,.19]}><sphereGeometry args={[1,24,16]}/><meshStandardMaterial color="#6b846c" roughness={.35} metalness={.4}/></mesh>
  {[-1,1].map(side=><group key={side}>
   <mesh position={[side*.15,.08,-.36]} scale={[.11,.13,.1]}><sphereGeometry args={[1,20,14]}/><meshStandardMaterial color="#a46343" roughness={.3} metalness={.4} emissive="#8d3e25" emissiveIntensity={.15}/></mesh>
   <mesh position={[side*.42,.13,.12]} rotation={[0,side*-.38,side*-.12]} scale={[.39,.018,.22]}><sphereGeometry args={[1,24,16]}/><meshPhysicalMaterial color="#c6efda" transparent opacity={.32} metalness={.1} roughness={.14} side={THREE.DoubleSide}/></mesh>
   <Line points={[[side*.07,.14,-.41],[side*.13,.23,-.58]]} color="#8dba9a" lineWidth={1}/>
  </group>)}
  {legs.map((points,i)=><Line key={i} points={points} color="#81a88d" lineWidth={1.1}/>)}
  <mesh><sphereGeometry args={[data.config.fly_radius,24,16]}/><meshBasicMaterial color={color} wireframe transparent opacity={collision?.55:.08}/></mesh>
  <mesh rotation={[-Math.PI/2,0,0]} position={[0,-.55,0]}><ringGeometry args={[data.config.fly_radius*1.3,data.config.fly_radius*1.3+.025,64]}/><meshBasicMaterial color={color} transparent opacity={.8}/></mesh>
  <Html position={[0,1.05,0]} center distanceFactor={25}><div className="object-label fly-label"><span className="status-dot"/>D. MELANOGASTER<span className="object-value">{number(sample.speed)} u/s</span></div></Html>
 </group>;
}

function World({data,sample,time,trails,fov,inspect}:{data:Replay;sample:Sample;time:number;trails:boolean;fov:boolean;inspect:(v:Inspection)=>void}){
 const dimension=data.config.world_dimension??2;
 const collided=data.metrics.failure?.kind==='collision'&&time>=data.metrics.failure.time_ms;
 const color=collided?'#ff7469':sample.rule==='threat'?'#ffb176':'#a3a9e3';
 const flyTrail=useMemo(()=>data.world.fly.slice(0,sample.worldIndex+1).map(p=>xyz(p,.02)),[data,sample.worldIndex]);
 const outline=useMemo(()=>{const x=data.config.bounds_xy?.[0]??[-50,50],y=data.config.bounds_xy?.[1]??[-50,50],z=data.config.world_dimension===3&&data.config.bounds?.[2]?data.config.bounds[2][0]:-1.72;return [[x[0],z,-y[0]],[x[1],z,-y[0]],[x[1],z,-y[1]],[x[0],z,-y[1]],[x[0],z,-y[0]]] as [number,number,number][]},[data]);
 const tangent=(data.config.camera_width??256)/(2*(data.config.camera_focal_px??160));
 return <group>
  <Line points={outline} color="#7aa28a" transparent opacity={.2}/>
  {dimension===3&&data.config.bounds?.length===3&&<group>{data.config.bounds[2].map((z,i)=><Line key={i} points={[[data.config.bounds![0][0],z,-data.config.bounds![1][0]],[data.config.bounds![0][1],z,-data.config.bounds![1][0]],[data.config.bounds![0][1],z,-data.config.bounds![1][1]],[data.config.bounds![0][0],z,-data.config.bounds![1][1]],[data.config.bounds![0][0],z,-data.config.bounds![1][0]]]} color="#7aa28a" transparent opacity={.2}/>)}</group>}
  {trails&&flyTrail.length>1&&<Line points={flyTrail} color="#b4efca" lineWidth={1.7} transparent opacity={.75}/>}
  {sample.obstacles.map((p,i)=>{const radius=data.scenario.obstacles[i]?.radius;if(!radius)return null;const track=data.world.obstacles.slice(0,sample.worldIndex+1).map(v=>xyz(v[i],.01));return <group key={data.scenario.obstacles[i].id}>
   {trails&&track.length>1&&<Line points={track} color="#9b9bc5" lineWidth={1} transparent opacity={.35}/>}
   <group position={xyz(p)} onClick={e=>{e.stopPropagation();inspect({kind:'obstacle',index:i})}}>
    <mesh><sphereGeometry args={[radius,40,28]}/><meshPhysicalMaterial color={color} roughness={.23} metalness={.2} transparent opacity={.12} emissive={color} emissiveIntensity={.2} depthWrite={false}/></mesh>
    <mesh><sphereGeometry args={[radius,24,12]}/><meshBasicMaterial color={color} wireframe transparent opacity={.35}/></mesh>
    <mesh rotation={[Math.PI/2,0,0]}><torusGeometry args={[radius,.012,6,72]}/><meshBasicMaterial color={color}/></mesh>
    <Html position={[0,radius+.9,0]} center distanceFactor={30}><div className="object-label"><span className="target-square"/>OBJECT {String(i+1).padStart(2,'0')}<span className="object-value">{number(p[0],1)}, {number(p[1],1)}</span></div></Html>
   </group>
  </group>})}
  {fov&&<group position={xyz(sample.fly)}><Line points={[[0,0,0],[-12*tangent,0,-12],[12*tangent,0,-12],[0,0,0]]} color="#79c3aa" transparent opacity={.16} dashed dashSize={.3} gapSize={.2}/></group>}
  <FruitFly data={data} sample={sample} inspect={inspect}/>
 </group>;
}

function layout(graph:Graph){
 const counts:Record<string,number>={},indices:Record<string,number>={};
 graph.nodes.forEach(n=>{const k=n.type+n.side;counts[k]=(counts[k]??0)+1});
 return graph.nodes.map(n=>{const k=n.type+n.side,i=indices[k]??0;indices[k]=i+1;const angle=i*2.399963229728653;const t=(i+.5)/counts[k];const sphere=Math.sqrt(1-(2*t-1)**2),radius=n.population==='readout'?.38:1.6;const center=n.type==='LC4'?-4:n.type==='LPLC2'?0:4;const side=n.side==='left'?-1:1;const yy=n.population==='readout'?(['DNp01','DNp02','DNp04','DNp06','DNp11'].indexOf(n.type)-2)*.8:side*2;return new THREE.Vector3(center+Math.cos(angle)*sphere*radius,yy+(2*t-1)*radius,side*1.7+Math.sin(angle)*sphere*radius)});
}

function NeuralGraph({graph,data,sample,edgeCutoff,signal,selected,inspect}:{graph:Graph;data:Replay;sample:Sample;edgeCutoff:number;signal:'activity'|'input';selected:number|null;inspect:(v:Inspection)=>void}){
 const mesh=useRef<THREE.InstancedMesh|null>(null),edgeGeometry=useRef<THREE.BufferGeometry|null>(null);
 const positions=useMemo(()=>layout(graph),[graph]);const indices=useMemo(()=>new Map(graph.nodes.map((n,i)=>[n.id,i])),[graph]);
 const edges=useMemo(()=>graph.edges.filter(e=>e.weight>=edgeCutoff&&(selected===null||e.source===selected||e.target===selected)).slice(0,1800),[graph,edgeCutoff,selected]);
 const edgePoints=useMemo(()=>new Float32Array(edges.flatMap(e=>[...positions[indices.get(e.source)!].toArray(),...positions[indices.get(e.target)!].toArray()])),[edges,positions,indices]);
 const edgeColors=useMemo(()=>new Float32Array(edges.length*6),[edges]);
 const ids=signal==='input'?data.encoder.ids:data.neural.kind==='anatomical'?data.neural.ids:[];
 const columns=useMemo(()=>new Map(ids.map((id,i)=>[Number(id),i])),[ids]);
 useEffect(()=>{if(!mesh.current)return;const dummy=new THREE.Object3D();graph.nodes.forEach((n,i)=>{dummy.position.copy(positions[i]);dummy.scale.setScalar(n.population==='readout'?.14:.065);dummy.updateMatrix();mesh.current!.setMatrixAt(i,dummy.matrix)});mesh.current.instanceMatrix.needsUpdate=true},[graph,positions]);
 useFrame(()=>{if(!mesh.current)return;const values=signal==='input'?sample.drive:data.neural.kind==='anatomical'?sample.neuralValues:null;let peak=0;if(values)for(const v of values)peak=Math.max(peak,Math.abs(v));const color=new THREE.Color();graph.nodes.forEach((n,i)=>{const column=columns.get(n.id),v=values&&column!==undefined?values[column]:null;const intensity=v===null?.2:peak>0?.22+.78*Math.sqrt(Math.max(0,v)/peak):.22;color.set(COLORS[n.type]??'#a6c8c4').multiplyScalar(selected===n.id?1.6:intensity);mesh.current!.setColorAt(i,color)});if(mesh.current.instanceColor)mesh.current.instanceColor.needsUpdate=true;
  edges.forEach((edge,i)=>{const column=columns.get(edge.source),v=values&&column!==undefined?values[column]:null;const strength=v!==null&&peak>0?Math.max(.08,Math.min(1,(v/peak)*edge.normalized*2)):.09;color.set('#a0f3cd').multiplyScalar(strength);for(let j=0;j<2;j++){edgeColors[i*6+j*3]=color.r;edgeColors[i*6+j*3+1]=color.g;edgeColors[i*6+j*3+2]=color.b}});const attr=edgeGeometry.current?.getAttribute('color');if(attr)attr.needsUpdate=true;
 });
 return <group position={[15,7,0]}>
  <Html position={[0,5.6,0]} center distanceFactor={32}><div className="neural-world-title">CIRCUIT V2<span>SCHEMATIC / {(signal==='activity'&&data.neural.kind!=='anatomical')||(signal==='input'&&(!sample.drive||sample.drive.length!==321))?'STRUCTURE ONLY':signal.toUpperCase()} / {edges.length} EDGES SHOWN</span></div></Html>
  <lineSegments><bufferGeometry ref={edgeGeometry}><bufferAttribute attach="attributes-position" args={[edgePoints,3]}/><bufferAttribute attach="attributes-color" args={[edgeColors,3]}/></bufferGeometry><lineBasicMaterial vertexColors transparent opacity={.42} depthWrite={false}/></lineSegments>
  <instancedMesh ref={mesh} args={[undefined,undefined,graph.nodes.length]} onClick={e=>{e.stopPropagation();if(e.instanceId!==undefined)inspect({kind:'neuron',node:graph.nodes[e.instanceId]})}}><sphereGeometry args={[1,10,8]}/><meshBasicMaterial color="white" toneMapped={false}/></instancedMesh>
  {[-4,0,4].map((x,i)=><Html key={x} position={[x,-4.7,0]} center distanceFactor={28}><span className="population-label">{['LC4','LPLC2','DESCENDING'][i]}</span></Html>)}
 </group>;
}

export function Scene({data,sample,graph,time,mode,reset,trails,fov,neurons,edgeCutoff,signal,inspection,inspect}:{data:Replay|null;sample:Sample|null;graph:Graph|null;time:number;mode:CameraMode;reset:number;trails:boolean;fov:boolean;neurons:boolean;edgeCutoff:number;signal:'activity'|'input';inspection:Inspection;inspect:(v:Inspection)=>void}){
 return <SceneBoundary><Canvas camera={{position:[27,22,34],fov:43,near:.05,far:220}} dpr={[1,1.7]} gl={{antialias:true,alpha:false,powerPreference:'high-performance'}} onPointerMissed={()=>inspect(null)}>
  <color attach="background" args={['#071011']}/><fog attach="fog" args={['#071011',38,125]}/>
  <ambientLight intensity={1.2}/><directionalLight position={[8,20,7]} intensity={2.2} color="#d3f5dd"/><pointLight position={[-8,8,-16]} intensity={25} color="#7795cf" distance={45}/>
  <Suspense fallback={null}><Arena data={data}/>{data&&sample&&<World data={data} sample={sample} time={time} trails={trails} fov={fov} inspect={inspect}/>} {data&&sample&&graph&&neurons&&<NeuralGraph graph={graph} data={data} sample={sample} edgeCutoff={edgeCutoff} signal={signal} selected={inspection?.kind==='neuron'?inspection.node?.id??null:null} inspect={inspect}/>}</Suspense>
  <CameraRig mode={mode} sample={sample} reset={reset}/>
 </Canvas></SceneBoundary>;
}
