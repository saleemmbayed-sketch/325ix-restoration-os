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
// GLTFLoader sanitizes ':' in node names; recover original glTF names first.
const modelKey=mesh=>{
 for(let node=mesh;node;node=node.parent){
  const name=node.userData?.name||node.name||'';
  const found=/^MX:([a-z0-9_]+):\d+$/.exec(name)||/^MX_([a-z0-9_]+?)_\d+(?:_\d+)?$/.exec(name);
  if(found)return found[1];
 }
 return null;
};
function clearMechanicalHighlight(){
 for(const [mesh,previous,clones] of state.highlighted){mesh.material=previous;for(const mat of clones)mat.dispose();}
 state.highlighted=[];
}
function mechanicalMeshes(key){return state.meshes.filter(mesh=>modelKey(mesh)===key)}
function highlightMechanical(key){
 clearMechanicalHighlight();
 for(const mesh of mechanicalMeshes(key)){
  const original=mesh.material,arr=Array.isArray(original)?original:[original];
  const tinted=arr.map(mat=>{const copy=mat.clone();if(copy.emissive){copy.emissive.set('#ffbc69');copy.emissiveIntensity=.48;}else copy.color?.set('#ffbc69');return copy});
  mesh.material=Array.isArray(original)?tinted:tinted[0];state.highlighted.push([mesh,original,tinted]);
 }
}
function setupEngineBonnet(model){
 state.hoodPivot=null;state.hoodOpened=false;
 if(state.mechanical?.slug!=='ix_m20_engine_bay')return;
 const hood=[];model.traverse(node=>{if(node.isMesh&&modelKey(node)==='bonnet')hood.push(node)});
 if(!hood.length)return;
 const pivot=new THREE.Group();pivot.name='Bonnet hinge — front edge';pivot.position.set(0,1.28,1.85);model.add(pivot);
 for(const mesh of hood)pivot.attach(mesh);state.hoodPivot=pivot;
}
function animateBonnet(open){
 if(!state.hoodPivot)return false;
 const pivot=state.hoodPivot,start=pivot.rotation.x,finish=open?1.13:0,started=performance.now();
 state.hoodOpened=open;
 const update=()=>{if(state.hoodPivot!==pivot)return;const p=Math.min(1,(performance.now()-started)/580);const smooth=p*p*(3-2*p);pivot.rotation.x=start+(finish-start)*smooth;if(p<1)requestAnimationFrame(update);};requestAnimationFrame(update);
 const button=$('ix-bonnet-action');if(button)button.textContent=open?'Close bonnet':'Open bonnet';return true;
}
export function toggleBonnet(){return animateBonnet(!state.hoodOpened)}
export function selectMechanicalComponent(key,notify=true){
 if(!state.mechanical||!mechanicalMeshes(key).length)return false;
 if(key==='bonnet'){toggleBonnet();return true;}
 if(state.hoodPivot&&!state.hoodOpened)animateBonnet(true);
 highlightMechanical(key);
 if(notify)window.ixOnMechanicalComponent?.(state.mechanical.slug,key);
 const selected=state.mechanical.components?.find(c=>c.id===key);
 const name=$('ix3d-mesh-name');if(name)name.textContent=(selected?.label||key.replaceAll('_',' '))+' · selectable model component';
 if($('ix3d-selection-info'))$('ix3d-selection-info').hidden=false;
 return true;
}
export function isolateMechanicalComponent(key){
 if(!state.mechanical)return false;
 state.isolated=state.isolated===key?null:key;
 for(const mesh of state.meshes){const id=modelKey(mesh);mesh.visible=!state.isolated||id===state.isolated||id==='engine_bay'||id==='strut_mount'||id==='subframe'}
 return Boolean(state.isolated);
}
export function focusMechanicalComponent(key){
 if(!selectMechanicalComponent(key))return false;
 const meshes=mechanicalMeshes(key);const box=new THREE.Box3();for(const m of meshes)box.expandByObject(m);
 const center=box.getCenter(new THREE.Vector3()),size=Math.max(box.getSize(new THREE.Vector3()).length(),.5);
 studio.controls.target.copy(center);studio.camera.position.copy(center).add(new THREE.Vector3(1,1.05,1.6).normalize().multiplyScalar(Math.max(size*2.9,state.modelSize*.8)));
 studio.controls.update();return true;
}

const REGIONS={
 chassis:['front_axle','steering','brakes','wheels','rear_axle'],
 drivetrain:['manual_transmission','clutch','gearshift','transfer_box_electric_gearbox','drive_shaft'],
 engine:['engine','radiator','fuel_preparation_system','fuel_supply','exhaust_system','engine_electrical_system'],
 electrical:['lighting','vehicle_electrical_system','instruments_measuring_systems','heater_and_air_conditioning','pedals']
};
let region='chassis';

const state={model:null,modelUrl:null,meshes:[],selected:null,selectedOriginal:null,explosion:0,wireframe:false,modelCenter:null,modelSize:1,wholeCar:true,mechanical:null,hoodPivot:null,hoodOpened:false,highlighted:[],isolated:null};
const setStatus=(s)=>{const el=$('twinvisualstatus');if(el)el.textContent=s;const hud=$('ix3d-status');if(hud)hud.textContent=s;};
function showFallback(error){
 const canvas=$('ix3d-stage');if(canvas)canvas.hidden=true;
 const svg=$('twin-canvas');if(svg)svg.setAttribute('hidden','');
 const msg=$('ix3d-fallback');if(msg){msg.hidden=false;msg.textContent=error+' · 2D evidence and catalog remain available.';}
 setStatus('3D unavailable · OEM catalog fallback active');
 if($('twin2d'))$('twin2d').click();
}
function makeStudio(){
 const holder=$('ix3d-stage');if(!holder)return null;
 if(studio&&studio.holder===holder)return studio;
 if(studio)studio.destroy();
 const scene=new THREE.Scene();scene.background=new THREE.Color('#101f31');
 const camera=new THREE.PerspectiveCamera(39,1,0.01,1500);
 let renderer;
 try{renderer=new THREE.WebGLRenderer({antialias:true,alpha:false,powerPreference:'high-performance'});}catch(e){showFallback('WebGL renderer unavailable: '+e.message);return null;}
 renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,1.5)); // Low-power Mac: avoid double-resolution GPU work.
 renderer.outputColorSpace=THREE.SRGBColorSpace;
 renderer.toneMapping=THREE.ACESFilmicToneMapping;
 renderer.toneMappingExposure=1.45;
 renderer.setClearColor('#101f31');
 holder.replaceChildren(renderer.domElement);
 const markers=document.createElement('div');markers.className='ix3d-markers';markers.setAttribute('aria-label','Approximate vehicle zones');holder.append(markers);
 const markerButtons=new Map();
 const syncMarkers=()=>{
  if(!state.modelCenter)return;
  const width=holder.clientWidth,height=holder.clientHeight;
  for(const [id,button] of markerButtons){
   if(button.hidden)continue;
   const v=HOTSPOT_HINTS[id];
   if(!v)continue;
   const point=state.modelCenter.clone().add(new THREE.Vector3(...v).multiplyScalar(state.modelSize)).project(camera);
   button.style.left=`${(point.x+1)*width/2}px`;
   button.style.top=`${(1-point.y)*height/2}px`;
   button.style.visibility=point.z>1||point.z< -1?'hidden':'visible';
  }
 };

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
 const tick=()=>{if(!alive)return;requestAnimationFrame(tick);if($('twin')?.hidden||holder.hidden)return;resize();controls.update();syncMarkers();renderer.render(scene,camera);};tick();
 const selectMesh=(mesh)=>{
   if(state.mechanical){if(mesh)selectMechanicalComponent(modelKey(mesh));return;}
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
 studio={holder,scene,camera,renderer,controls,grid,markers,markerButtons,selectMesh,resize,destroy};
 return studio;
}
function frameModel(){if(!studio||!state.model)return;
 const bbox=new THREE.Box3().setFromObject(state.model);const center=bbox.getCenter(new THREE.Vector3());const dimensions=bbox.getSize(new THREE.Vector3());const radius=Math.max(dimensions.length()*.5,1);
 state.modelCenter=center;state.modelSize=radius;studio.controls.target.copy(center);
 studio.grid.position.y=bbox.min.y-.02*radius;
 // Keep assemblies legible on a laptop and view the bonnet from the cabin side.
 const isEngine=state.mechanical?.slug==='ix_m20_engine_bay';
 const aim=isEngine?new THREE.Vector3(1.1,1.6,-1.65):new THREE.Vector3(1.6,1.0,1.7);
 studio.camera.position.copy(center).add(aim.multiplyScalar(radius*(isEngine?1.15:1.12)));
 studio.camera.near=Math.max(radius/1000,.005);studio.camera.far=Math.max(radius*55,200);studio.camera.updateProjectionMatrix();
 studio.controls.minDistance=radius*.4;studio.controls.maxDistance=radius*10;studio.controls.update();
}
function setExplosion(fraction){state.explosion=fraction;if(!state.modelCenter||!studio)return;
 for(const mesh of state.meshes){mesh.position.copy(mesh.userData.ixOriginalPosition);
  if(state.mechanical&&['bonnet','engine_bay','bulkhead','strut_mount','radiator_support'].includes(modelKey(mesh)))continue;const worldDirection=mesh.userData.ixExplodeWorld;
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
async function loadBinarySTL(src){
 const response=await fetch(src);
 if(!response.ok)throw Error('Local STL fetch failed: HTTP '+response.status);
 const buffer=await response.arrayBuffer(),view=new DataView(buffer);
 if(buffer.byteLength<84)throw Error('Invalid binary STL length');
 const count=view.getUint32(80,true);
 if(84+count*50!==buffer.byteLength)throw Error('Only binary STL is supported');
 const positions=new Float32Array(count*9);
 for(let t=0;t<count;t++){
  const offset=84+t*50;
  for(let k=0;k<9;k++)positions[t*9+k]=view.getFloat32(offset+12+4*k,true);
 }
 const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.BufferAttribute(positions,3));geometry.computeVertexNormals();
 const mesh=new THREE.Mesh(geometry,new THREE.MeshStandardMaterial({color:0x8daebc,roughness:.55,metalness:.18,side:THREE.DoubleSide}));
 mesh.name='Personal STL reference · not OEM-certified';const group=new THREE.Group();group.add(mesh);return group;
}
async function loadModel(src,data,format='glb',wholeCar=true,mechanical=null){
 const s=makeStudio();if(!s)return;
 clearMechanicalHighlight();s.selectMesh(null);
 if(state.model){s.scene.remove(state.model);state.model=null;}
 state.mechanical=mechanical;state.isolated=null;state.hoodPivot=null;state.hoodOpened=false;
 setStatus(mechanical?'Preparing inspectable mechanical assembly…':'Loading licensed E30 geometry…');
 const loader=new GLTFLoader();loader.setMeshoptDecoder(MeshoptDecoder);
 try {
  const model=format==='stl'?await loadBinarySTL(src):(await new Promise((resolve,reject)=>loader.load(src,resolve,undefined,reject))).scene;
  state.model=model;state.modelUrl=src;state.wholeCar=wholeCar;s.scene.add(model);
  if(mechanical)setupEngineBonnet(model);
  prepareMeshes(model);frameModel();
  $('ix3d-stage').hidden=false;$('twin-diagram-panel').hidden=true;$('twin-canvas').setAttribute('hidden','');$('ix3d-fallback').hidden=true;const m3=$('ix-mode-3d'),m2=$('twin2d');m3?.classList.add('active');m2?.classList.remove('active');if($('ix-stage-heading'))$('ix-stage-heading').textContent='3D VIEW';
  setExplosion(Number($('ix3d-explode')?.value||0)/100);
  setStatus(mechanical?`${mechanical.components.length} selectable components · ${mechanical.description} · illustrated reference`:
    `${state.meshes.length} pickable reference meshes · ${wholeCar?'E30 body':'personal assembly'} · NOT 325iX CAD · variant/fitment not verified`);
  renderSystems(data);
  const regs=$('ix3d-regions');if(regs)regs.hidden=Boolean(mechanical);
  if(mechanical?.slug==='ix_m20_engine_bay')setTimeout(()=>animateBonnet(true),350);
 }catch(e){showFallback('Cannot load the E30 model: '+(e?.message||e));throw e;}
}
function renderSystems(data){
 const menu=$('ix3d-system-select');if(!menu)return;
 if(studio){
  const all=(state.wholeCar&&!state.mechanical?data.systems:[]).filter(s=>HOTSPOT_HINTS[s.id]);
  studio.markers.replaceChildren();studio.markerButtons.clear();
  for(const system of all){
   const button=document.createElement('button');button.type='button';button.className='ix3d-marker';
   button.dataset.system=system.id;button.title=system.label+' — approximate vehicle location';
   button.setAttribute('aria-label','Explore '+system.label+' reference zone');
   button.textContent=system.label;button.onclick=()=>focusSystem(system.id);
   studio.markers.append(button);studio.markerButtons.set(system.id,button);
  }
  filterRegion();
 }

 const value=menu.value;menu.replaceChildren();const lead=new Option('Choose an iX system', '');menu.add(lead);
 for(const s of data.systems||[]){const opt=new Option(s.label+' · '+s.assembly_count+' assemblies',s.id);menu.add(opt);}if(data.systems?.some(s=>s.id===value))menu.value=value;
}
function filterRegion(){
 if(!studio)return;
 for(const [id,button] of studio.markerButtons){
  button.hidden=!REGIONS[region]?.includes(id);
  button.classList.toggle('selected',$('ix3d-system-select')?.value===id);
 }
 document.querySelectorAll('[data-ix-region]').forEach(b=>{
  b.classList.toggle('active',b.dataset.ixRegion===region);
  b.setAttribute('aria-pressed',String(b.dataset.ixRegion===region));
 });
}
function focusSystem(id){
 const data=window.visualTwinData,system=data?.systems?.find(s=>s.id===id);
 if(!system)return;
 const group=Object.entries(REGIONS).find(([_,ids])=>ids.includes(id));if(group)region=group[0];
 const menu=$('ix3d-system-select');if(menu)menu.value=id;
 filterRegion();
 const hint=HOTSPOT_HINTS[id];
 if(studio&&state.modelCenter&&hint){
  const target=state.modelCenter.clone().add(new THREE.Vector3(...hint).multiplyScalar(state.modelSize));
  const shift=target.sub(studio.controls.target);
  studio.controls.target.add(shift);studio.camera.position.add(shift);studio.controls.update();
 }
 window.ixSelectVisualSystemById?.(id);
}
function pickSystem(){focusSystem($('ix3d-system-select')?.value)}
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
  for(const b of document.querySelectorAll('[data-ix-region]'))b.addEventListener('click',()=>{region=b.dataset.ixRegion;filterRegion();});
  for(const b of document.querySelectorAll('[data-ix3d-view]'))b.addEventListener('click',()=>positionView(b.dataset.ix3dView));
  $('ix3d-wireframe')?.addEventListener('change',e=>wireframe(e.target.checked));
  $('ix3d-local-model')?.addEventListener('change',e=>{const file=e.target.files?.[0];if(!file)return;if(!/\.(glb|gltf)$/i.test(file.name)){setStatus('Choose a GLB or glTF file');return}const url=URL.createObjectURL(file);loadModel(url,data).finally(()=>URL.revokeObjectURL(url));});
 }
 if(state.model&&studio&&studio.holder===$('ix3d-stage'))return;
 await loadModel('/models/e30_reference_m3.glb',data);
}
export {positionView};
export async function openPersonal(src,format,data,wholeCar=false){
 if(format!=='glb'&&format!=='stl')throw Error('Only GLB or binary STL can be displayed');
 await loadModel(src,data,format,wholeCar);
}
export async function openMechanical(scene,data){
 if(!scene?.filename?.startsWith('models/ix_')||!Array.isArray(scene.components))throw Error('Unknown mechanical scene');
 await loadModel('/'+scene.filename,data,'glb',false,scene);
 return {components:scene.components.length,pickable:state.meshes.length};
}


export function reset(){if(studio&&state.modelCenter)studio.controls.target.copy(state.modelCenter);positionView('iso');if($('ix3d-explode')){$('ix3d-explode').value='0';$('ix3d-explode-value').textContent='0%'}setExplosion(0);studio?.selectMesh(null);}
export function selectSystem(id){const select=$('ix3d-system-select');if(select)select.value=id;filterRegion();}
