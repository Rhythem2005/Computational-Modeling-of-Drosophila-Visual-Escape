import {useMemo,useRef} from 'react';
import {useFrame} from '@react-three/fiber';
import {Html,Line} from '@react-three/drei';
import * as THREE from 'three';
import {isTable} from './presentation';
import type {WorldConfig,SolidPart} from './types';
import {roomDimensions,worldToDisplay as xyz,displayQuaternion} from './roomDesign';

export function SolidParts({parts}:{parts:SolidPart[]}){return <>{parts.map((p,i)=><group key={i} position={xyz(p.offset)} quaternion={displayQuaternion(p.quaternion)}><mesh>{p.shape==='sphere'?<sphereGeometry args={[p.radius??0,32,20]}/>:<boxGeometry args={[(p.half_extents?.[0]??0)*2,(p.half_extents?.[2]??0)*2,(p.half_extents?.[1]??0)*2]}/>}<meshStandardMaterial color={new THREE.Color(...p.color.map(v=>v/255) as [number,number,number])} metalness={.18} roughness={.48}/></mesh></group>)}</>}

function Surface({position,normal,width,height,color,floor=false}:{position:THREE.Vector3;normal:THREE.Vector3;width:number;height:number;color:THREE.Color;floor?:boolean}){
 const group=useRef<THREE.Group>(null);
 const q=useMemo(()=>new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0,0,1),normal),[normal]);
 useFrame(({camera})=>{if(group.current)group.current.visible=camera.position.clone().sub(position).dot(normal)<.1});
 // Cut away only spectator-facing walls. Physics and RGB cameras stay closed.
 return <group ref={group} position={position} quaternion={q}>
  <mesh><planeGeometry args={[width,height]}/><meshStandardMaterial color={color} roughness={.9} side={THREE.DoubleSide}/></mesh>
  {Array.from({length:9},(_,i)=><Line key={i} points={[[-width/2,height*(i/8-.5),-.015],[width/2,height*(i/8-.5),-.015]]} color={floor?'#25272d':'#21232a'} lineWidth={.6}/>)}
  {Array.from({length:9},(_,i)=><Line key={i} points={[[width*(i/8-.5),-height/2,-.015],[width*(i/8-.5),height/2,-.015]]} color={floor?'#25272d':'#21232a'} lineWidth={.6}/>)}
  <Line points={[[-width/2,-height/2,-.025],[width/2,-height/2,-.025],[width/2,height/2,-.025],[-width/2,height/2,-.025],[-width/2,-height/2,-.025]]} color="#48514f" lineWidth={1.2}/>
 </group>;
}

export function RoomEnvironment({config,furniture=false}:{config:WorldConfig;furniture?:boolean}){
 const {center,size}=roomDimensions(config);
 const color=new THREE.Color('#111216'); // Spectator finish only; saved RGB sensors are untouched.
 const surfaces=useMemo(()=>size.flatMap((_,axis)=>[-1,1].map(side=>{
  const p=new THREE.Vector3(...center),n=new THREE.Vector3();p.setComponent(axis,p.getComponent(axis)+side*size[axis]/2);n.setComponent(axis,side);
  const widths=axis===0?[size[2],size[1]]:axis===1?[size[0],size[2]]:[size[0],size[1]];
  return {position:p,normal:n,width:widths[0],height:widths[1],floor:axis===1&&side===-1};
 })),[...center,...size]);
 return <group>
  {surfaces.map((s,i)=><Surface key={i} {...s} color={color}/>)}
  {config.room_scene?.static_solids.filter(s=>furniture||!isTable(s.id)).map(s=><group key={s.id} position={xyz(s.keyframes[0].position)}><SolidParts parts={s.parts}/><Html center position={[0,6,0]}><span className="world-coordinate">{s.id.toUpperCase().replaceAll('_',' ')} / SOLID COLLISION VOLUME</span></Html></group>)}
  <Html center position={[center[0],center[1]-size[1]/2+.2,center[2]-size[2]*.38]}><span className="world-coordinate">BOUNDED 3D ROOM / SPECTATOR CUTAWAY</span></Html>
 </group>;
}
