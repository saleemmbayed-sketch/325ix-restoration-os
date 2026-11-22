/* BMW 325iX Restoration OS — independent Three.js visual layer.
 * Real model = E30 M3 exterior reference only; hotspots are non-dimensional.
 * Source geometry: Martin Trafas (TinoD2), CC BY 4.0, see docs/3D_ASSETS.md.
 * Three.js + meshoptimizer are MIT and prepared locally for offline work.
 */
import * as THREE from '/vendor/three/build/three.module.js';
import { OrbitControls } from '/vendor/three/examples/jsm/controls/OrbitControls.js';
import { GLTFLoader } from '/vendor/three/examples/jsm/loaders/GLTFLoader.js';
import { MeshoptDecoder } from '/vendor/meshopt_decoder.module.js';

let studio=null;
const HOTSPOT_HINTS = {
 engine:[-.33,.18,.23], radiator:[-.73,.18,.24], fuel_preparation_system:[-.25,.27,-.1],
 fuel_supply:[.15,-.22,.02], exhaust_system:[.15,-.25,-.22],manual_transmission:[-.06,-.07,.15],
 clutch:[-.12,.01,.15],gearshift:[.02,.23,.10],pedals:[-.17,.16,.25],
 transfer_box_electric_gearbox:[.17,-.13,.11],drive_shaft:[.38,-.22,.10],
 front_axle:[-.55,-.30,.1], rear_axle:[.60,-.30,.1],steering:[-.59,.05,.29],
 wheels:[.48,-.30,.42],brakes:[-.54,-.29,.42],vehicle_electrical_system:[.05,.37,-.21],
 engine_electrical_system:[-.35,.34,.03],lighting:[-.77,.13,.22],instruments_measuring_systems:[-.14,.40,.16],
 heater_and_air_conditioning:[-.02,.37,.14]
};
const $=id=>document.getElementById(id);
const state={model:null,modelUrl:null,meshes:[],selected:null,selectedOriginal:null,explosion:0,wireframe:false,modelCenter:null,modelSize:1};
const setStatus=(s)=>{const el=$('twinvisualstatus');if(el)el.textContent=s;const hud=$('ix3d-status');if(hud)hud.textContent=s;};
function showFallback(error){
 const canvas=$('ix3d-stage');if(canvas)canvas.hidden=true;
 const svg=$('twin-canvas');if(svg)svg.hidden=false;
 const msg=$('ix3d-fallback');if(msg){msg.hidden=false;msg.textContent=error+' · 2D evidence and catalog remain available.';}
 setStatus('3D unavailable · verified 2D catalog fallback active');
}
function makeStudio(){
 const holder=$('ix3d-stage');if(!holder)return null;
 if(studio&&studio.holder===holder)return studio;
 if(studio)studio.destroy();
 const scene=new THREE.Scene();scene.background=new THREE.Color('#0c1420');
 const camera=new THREE.PerspectiveCamera(39,1,0.01,1500);
 let renderer;
 try{renderer=new THREE.WebGLRenderer({antialias:true,alpha:false,powerPreference:'high-performance'});}catch(e){showFallback('WebGL renderer unavailable: '+e.message);return null;}
 renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,2));
 renderer.outputColorSpace=THREE.SRGBColorSpace;
 renderer.toneMapping=THREE.ACESFilmicToneMapping;
 renderer.toneMappingExposure=1.45;
 renderer.setClearColor('#0c1420');
 holder.replaceChildren(renderer.domElement);
 renderer.domElement.setAttribute('aria-label','Rotatable E30 reference model: drag to orbit, scroll to zoom, click meshes');
 renderer.domElement.setAttribute('role','img');
 const ambient=new THREE.HemisphereLight(0xe1f1ff,0x151923,2.5);scene.add(ambient);
 const key=new THREE.DirectionalLight(0xffffff,3.5);key.position.set(7,10,5);scene.add(key);
 const edge=new THREE.DirectionalLight(0x72b8ff,1.3);edge.position.set(-7,4,-7);scene.add(edge);
 const fill=new THREE.DirectionalLight(0xffffff,1.3);fill.position.set(-3,4,8);scene.add(fill);
 const grid=new THREE.GridHelper(22,44,0x36506a,0x1b3145);
 grid.material.transparent=true;grid.material.opacity=.25;scene.add(grid);
 const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.dampingFactor=.08;
 controls.maxPolarAngle=Math.PI*.9;
 const raycaster=new THREE.Raycaster(),point=new THREE.Vector2();
 let alive=true, lastWidth=0,lastHeight=0;
 const resize=()=>{const w=Math.max(1,holder.clientWidth),h=Math.max(1,holder.clientHeight);if(w!==lastWidth||h!==lastHeight){camera.aspect=w/h;camera.updateProjectionMatrix();renderer.setSize(w,h,false);lastWidth=w;lastHeight=h;}};
 const tick=()=>{if(!alive)return;requestAnimationFrame(tick);if($('twin')?.hidden)return;resize();controls.update();renderer.render(scene,camera);};tick();
 const selectMesh=(mesh)=>{
   if(state.selected&&state.selectedOriginal){const old=state.selected;const cloned=old.material;old.material=state.selectedOriginal;(Array.isArray(cloned)?cloned:[cloned]).forEach(m=>m.dispose?.());}
   state.selected=mesh;state.selectedOriginal=null;
   if(mesh){const old=mesh.material;state.selectedOriginal=old;const tint=mat=>{const c=mat.clone();if(c.emissive){c.emissive.set('#f2a84a');c.emissiveIntensity=.5;}else if(c.color){c.color.set('#f2a84a');}return c;};mesh.material=Array.isArray(old)?old.map(tint):tint(old);
     $('ix3d-mesh-name').textContent=(mesh.name||'Unnamed mesh')+' · reference geometry only';
     const selected=$('ix3d-selection-info');if(selected)selected.hidden=false;
   }
 };
 const onClick=e=>{if(!state.meshes.length)return;const r=renderer.domElement.getBoundingClientRect();point.set((e.clientX-r.left)/r.width*2-1,-((e.clientY-r.top)/r.height)*2+1);raycaster.setFromCamera(point,camera);const hit=raycaster.intersectObjects(state.meshes,false)[0];if(hit)selectMesh(hit.object);};
 renderer.domElement.addEventListener('click',onClick);
 const destroy=()=>{alive=false;renderer.domElement.removeEventListener('click',onClick);controls.dispose();renderer.dispose();holder.replaceChildren();};
 studio={holder,scene,camera,renderer,controls,grid,selectMesh,resize,destroy};
 return studio;
}
function frameModel(){if(!studio||!state.model)return;
 const bbox=new THREE.Box3().setFromObject(state.model);const center=bbox.getCenter(new THREE.Vector3());const dimensions=bbox.getSize(new THREE.Vector3());const radius=Math.max(dimensions.length()*.5,1);
 state.modelCenter=center;state.modelSize=radius;studio.controls.target.copy(center);
 studio.grid.position.y=bbox.min.y-.02*radius;
 studio.camera.position.copy(center).add(new THREE.Vector3(1.6,.85,1.7).multiplyScalar(radius*1.5));
 studio.camera.near=Math.max(radius/1000,.005);studio.camera.far=Math.max(radius*55,200);studio.camera.updateProjectionMatrix();
 studio.controls.minDistance=radius*.4;studio.controls.maxDistance=radius*10;studio.controls.update();
}
function setExplosion(fraction){state.explosion=fraction;if(!state.modelCenter||!studio)return;
 for(const mesh of state.meshes){mesh.position.copy(mesh.userData.ixOriginalPosition);const worldDirection=mesh.userData.ixExplodeWorld;
  if(worldDirection.lengthSq()<.00001)continue;
  const parent=mesh.parent;parent.updateWorldMatrix(true,false);
  const a=parent.worldToLocal(worldDirection.clone().add(mesh.userData.ixExplodeOrigin));
  const b=parent.worldToLocal(mesh.userData.ixExplodeOrigin.clone());
  mesh.position.add(a.sub(b).multiplyScalar(state.modelSize*.95*fraction));
 }
}
function prepareMeshes(model){
 const bbox=new THREE.Box3().setFromObject(model);state.modelCenter=bbox.getCenter(new THREE.Vector3());state.modelSize=Math.max(1,bbox.getSize(new THREE.Vector3()).length()*.5);
 state.meshes=[];
 model.traverse(node=>{if(!node.isMesh)return;
  node.userData.ixOriginalPosition=node.position.clone();
  const center=new THREE.Box3().setFromObject(node).getCenter(new THREE.Vector3());
  const offset=center.clone().sub(state.modelCenter);
  node.userData.ixExplodeWorld=offset.lengthSq()>.00001?offset.normalize():new THREE.Vector3(0,1,0);
  node.userData.ixExplodeOrigin=center;
  node.castShadow=false;node.receiveShadow=false;
  state.meshes.push(node);
 });
}
async function loadModel(src, data){
 const s=makeStudio();if(!s)return;
 s.selectMesh(null);if(state.model){s.scene.remove(state.model);state.model=null;}
 setStatus('Loading licensed E30 geometry…');
 const loader=new GLTFLoader();loader.setMeshoptDecoder(MeshoptDecoder);
 try {
  const result=await new Promise((resolve,reject)=>loader.load(src,resolve,undefined,reject));
  state.model=result.scene;state.modelUrl=src;s.scene.add(result.scene);prepareMeshes(result.scene);frameModel();
  $('ix3d-stage').hidden=false;$('twin-canvas').hidden=true;$('ix3d-fallback').hidden=true;
  setExplosion(Number($('ix3d-explode')?.value||0)/100);
  setStatus(`${state.meshes.length} pickable reference meshes · 3D active · NOT 325iX CAD`);
  renderSystems(data);
 }catch(e){showFallback('Cannot load the E30 model: '+(e?.message||e));}
}
function renderSystems(data){
 const menu=$('ix3d-system-select');if(!menu)return;
 const value=menu.value;menu.replaceChildren();const lead=new Option('Choose an iX system', '');menu.add(lead);
 for(const s of data.systems||[]){const opt=new Option(s.label+' · '+s.assembly_count+' assemblies',s.id);menu.add(opt);}if(data.systems?.some(s=>s.id===value))menu.value=value;
}
function pickSystem(){const menu=$('ix3d-system-select');const id=menu?.value;
 if(!id)return;const data=window.visualTwinData,system=data?.systems?.find(s=>s.id===id);if(!system)return;
 const v=HOTSPOT_HINTS[id];if(v&&studio&&state.modelCenter){
  const focus=state.modelCenter.clone().add(new THREE.Vector3(...v).multiplyScalar(state.modelSize));
  studio.controls.target.lerp(focus,.5);studio.controls.update();
 }
 window.ixSelectVisualSystemById?.(id);
}
function positionView(view){if(!studio||!state.modelCenter)return;const c=studio.controls.target.clone(),r=state.modelSize*2.4;
 const vectors={front:[0,.6,1],rear:[0,.6,-1],side:[1,.6,0],top:[0,1,.001],iso:[1.6,.85,1.7]};
 const axis=new THREE.Vector3(...(vectors[view]||vectors.iso)).normalize();studio.camera.position.copy(c).addScaledVector(axis,r);studio.controls.update();
}
function wireframe(on){state.wireframe=on;for(const mesh of state.meshes){const materials=Array.isArray(mesh.material)?mesh.material:[mesh.material];materials.forEach(m=>{if('wireframe' in m)m.wireframe=on;});}}
export async function mount(data){
 if(!$('ix3d-stage'))return;
 renderSystems(data);
 if(!$('ix3d-stage').dataset.ixEvents){
  $('ix3d-stage').dataset.ixEvents='1';
  $('ix3d-explode')?.addEventListener('input',e=>{setExplosion(Number(e.target.value)/100);$('ix3d-explode-value').textContent=e.target.value+'%';});
  $('ix3d-system-select')?.addEventListener('change',pickSystem);
  for(const b of document.querySelectorAll('[data-ix3d-view]'))b.addEventListener('click',()=>positionView(b.dataset.ix3dView));
  $('ix3d-wireframe')?.addEventListener('change',e=>wireframe(e.target.checked));
  $('ix3d-local-model')?.addEventListener('change',e=>{const file=e.target.files?.[0];if(!file)return;if(!/\.(glb|gltf)$/i.test(file.name)){setStatus('Choose a GLB or glTF file');return}const url=URL.createObjectURL(file);loadModel(url,data).finally(()=>URL.revokeObjectURL(url));});
 }
 if(state.model&&studio&&studio.holder===$('ix3d-stage'))return;
 await loadModel('/models/e30_reference_m3.glb',data);
}
export function reset(){positionView('iso');if($('ix3d-explode')){$('ix3d-explode').value='0';$('ix3d-explode-value').textContent='0%'}setExplosion(0);studio?.selectMesh(null);}
export function selectSystem(id){const select=$('ix3d-system-select');if(select)select.value=id;}
