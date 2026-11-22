/* Parametric, non-destructive exploded-view hierarchy for glTF/Three.js.
 * Geometry is never permanently moved, baked or rewritten by the controller.
 * Naming/geometry do not imply BMW engineering verification.
 */
import * as THREE from '/vendor/three/build/three.module.js';

const DIR = Object.freeze({
 Hood:[0,1,.3], Roof:[0,1,0], Chassis:[0,-1,0], Interior:[0,1,0],
 Doors_Left:[-1,.08,0], Doors_Right:[1,.08,0], Wheels_Left:[-1,0,0],
 Wheels_Right:[1,0,0], Front_Bumper:[0,.05,1], Rear_Bumper:[0,.05,-1],
 Engine_Assembly:[0,1,.25], Suspension:[1,-.25,0], Steering:[-1,0,.2],
 Cooling:[0,.3,1], Drivetrain:[0,-.3,-1], Body_Exterior:[0,1,0],
 Electrical:[-.3,.5,0]
});
const SYSTEM_TO_GROUP = Object.freeze({
 engine:'Engine_Assembly', engine_electrical_system:'Electrical', radiator:'Cooling',
 front_axle:'Suspension', rear_axle:'Suspension', steering:'Steering', brakes:'Suspension',
 wheels:'Suspension', transfer_box_electric_gearbox:'Drivetrain', drive_shaft:'Drivetrain',
 manual_transmission:'Drivetrain', fuel_supply:'Engine_Assembly', fuel_preparation_system:'Engine_Assembly',
 exhaust_system:'Engine_Assembly', vehicle_electrical_system:'Electrical', bodywork:'Body_Exterior'
});
const parseId = node => {
  const n = node.userData?.name || node.name || '';
  return /^MX:([\w-]+):\d+$/.exec(n)?.[1] || /^MX_([\w-]+?)_\d+(?:_\d+)?$/.exec(n)?.[1] || null;
};
const clamp = f => Math.max(0, Math.min(1, Number.isFinite(Number(f)) ? Number(f) : 0));
const token = name => String(name || '').toLowerCase().replace(/[^a-z0-9]+/g,'_');
function roleFor(mesh, context){
  // Importers may already provide authored parent-child subassemblies.
  // Keep these explicit semantic labels instead of classifying from surface coordinates.
  let authoredRole=null,authoredComponent=null;
  for(let ancestor=mesh.parent;ancestor&&ancestor.type!=='Scene';ancestor=ancestor.parent){
    if(ancestor.name?.startsWith('Assembly:'))authoredRole=ancestor.name.slice(9);
    if(ancestor.name?.startsWith('Component:'))authoredComponent=ancestor.name.slice(10);
  }
  if(authoredRole)return {role:authoredRole,component:authoredComponent||mesh.name||mesh.uuid,label:authoredComponent||mesh.name||'Component'};
  const componentId=parseId(mesh);
  if(componentId){
    const meta=context.components?.find(c=>c.id===componentId);
    const role=SYSTEM_TO_GROUP[meta?.system] || (context.slug?.includes('front_axle')?'Suspension':context.slug?.includes('awd')?'Drivetrain':'Engine_Assembly');
    return {role, component:componentId, label:meta?.label || componentId};
  }
  const name=token(mesh.name);const x=new THREE.Box3().setFromObject(mesh).getCenter(new THREE.Vector3());
  if(/bonnet|hood/.test(name))return {role:'Hood',component:'hood',label:'Hood'};
  if(/roof/.test(name))return {role:'Roof',component:'roof',label:'Roof'};
  if(/door/.test(name))return {role:x.x<0?'Doors_Left':'Doors_Right',component:mesh.name||'door',label:mesh.name||'Door'};
  if(/wheel|tire|tyre|rim/.test(name))return {role:x.x<0?'Wheels_Left':'Wheels_Right',component:mesh.name||'wheel',label:mesh.name||'Wheel'};
  if(/bumper/.test(name))return {role:x.z>=0?'Front_Bumper':'Rear_Bumper',component:mesh.name||'bumper',label:mesh.name||'Bumper'};
  if(/engine|motor|cylinder|intake/.test(name))return {role:'Engine_Assembly',component:mesh.name||'engine',label:mesh.name||'Engine'};
  if(/suspension|strut|spring|axle|brake/.test(name))return {role:'Suspension',component:mesh.name||'suspension',label:mesh.name||'Suspension'};
  if(/dash|seat|interior|steering_wheel/.test(name))return {role:'Interior',component:mesh.name||'interior',label:mesh.name||'Interior'};
  if(/chassis|frame|underbody|floor/.test(name))return {role:'Chassis',component:mesh.name||'chassis',label:mesh.name||'Chassis'};
  return {role:'Body_Exterior',component:mesh.name||mesh.uuid,label:mesh.name||'Body mesh'};
}
/** A deterministic geometric *surface* centroid: no material density is inferred. */
function surfaceCenter(meshes){
  const sum=new THREE.Vector3();let weight=0;const point=new THREE.Vector3();
  for(const mesh of meshes){
    const a=mesh.geometry?.attributes?.position;
    if(!a)continue;
    mesh.updateWorldMatrix(true,false);
    const index=mesh.geometry.index, triangles=index?index.count/3:Math.floor(a.count/3);
    // Area weighted centroid supports open shell meshes. Sparse sampling bounds cost for dense CAD.
    const step=Math.max(1,Math.ceil(triangles/18000));
    const x=new THREE.Vector3(),y=new THREE.Vector3(),z=new THREE.Vector3();
    for(let i=0;i<triangles;i+=step){
      const j=3*i, ia=index?index.getX(j):j,ib=index?index.getX(j+1):j+1,ic=index?index.getX(j+2):j+2;
      x.fromBufferAttribute(a,ia).applyMatrix4(mesh.matrixWorld);y.fromBufferAttribute(a,ib).applyMatrix4(mesh.matrixWorld);z.fromBufferAttribute(a,ic).applyMatrix4(mesh.matrixWorld);
      const area=y.clone().sub(x).cross(z.clone().sub(x)).length()/2;
      if(area<1e-12)continue;
      point.copy(x).add(y).add(z).multiplyScalar(1/3);sum.addScaledVector(point,area*step);weight+=area*step;
    }
  }
  if(weight>0)return sum.divideScalar(weight);
  const box=new THREE.Box3();meshes.forEach(m=>box.expandByObject(m));return box.getCenter(new THREE.Vector3());
}
function axisFor(role, center, origin){
  if(DIR[role])return new THREE.Vector3(...DIR[role]).normalize();
  const v=center.clone().sub(origin);return v.lengthSq()>.000001?v.normalize():new THREE.Vector3(0,1,0);
}

export class ExplosionRig {
  constructor(root, context={}) {
    this.root=root;this.context=context;this.groups=new Map();this.components=new Map();
    this.factor=0;this.scope=null;this.isolated=false;this.listeners=new Set();this.exempt=new Set();
    root.updateWorldMatrix(true,true);
    const originalMeshes=[];root.traverse(n=>{if(n.isMesh)originalMeshes.push(n)});
    this.origin=new THREE.Vector3(0,0,0);
    this.origin.applyMatrix4(root.matrixWorld); // vehicle local (0,0,0) as required
    const bounds=new THREE.Box3();originalMeshes.forEach(m=>bounds.expandByObject(m));
    this.scale=Math.max(.5,bounds.getSize(new THREE.Vector3()).length()*.5);
    const grouped=new Map();
    for(const mesh of originalMeshes){
      const role=roleFor(mesh,context);const key=role.role;
      if(!grouped.has(key))grouped.set(key,new Map());
      if(!grouped.get(key).has(role.component))grouped.get(key).set(role.component,{meshes:[],label:role.label});
      grouped.get(key).get(role.component).meshes.push(mesh);
    }
    // Always construct pivots around the *whole* assembly before reparenting any mesh.
    const metadata=[];
    for(const [key,components] of grouped){
      const meshes=[...components.values()].flatMap(c=>c.meshes);
      const center=surfaceCenter(meshes),children=new Map();
      const subcenters=new Map([...components].map(([id,c])=>[id,surfaceCenter(c.meshes)]));
      metadata.push({key,components,center,subcenters,meshes,children});
    }
    for(const g of metadata){
      const group=new THREE.Group();group.name='Assembly:'+g.key;
      root.add(group);group.position.copy(root.worldToLocal(g.center.clone()));group.updateWorldMatrix(true,false);
      const axisWorld=axisFor(g.key,g.center,this.origin);
      const axisLocal=axisWorld.clone().transformDirection(new THREE.Matrix4().copy(root.matrixWorld).invert());
      const record={id:g.key,node:group,base:group.position.clone(),axis:axisLocal,children:g.children};
      this.groups.set(g.key,record);
      for(const [id,detail] of g.components){
        const pivot=new THREE.Group();pivot.name='Component:'+id;group.add(pivot);
        pivot.position.copy(group.worldToLocal(g.subcenters.get(id).clone()));pivot.updateWorldMatrix(true,false);
        for(const mesh of detail.meshes)pivot.attach(mesh); // keeps world geometry unchanged
        const vector=g.subcenters.get(id).clone().sub(g.center);
        if(vector.lengthSq()<1e-8)vector.copy(axisWorld);
        vector.normalize().transformDirection(new THREE.Matrix4().copy(group.matrixWorld).invert());
        const rec={id,label:detail.label,role:g.key,node:pivot,base:pivot.position.clone(),axis:vector,meshes:detail.meshes};
        g.children.set(id,rec);this.components.set(id,rec);
      }
    }
    this.apply();
  }
  apply(){
    for(const g of this.groups.values()){
      const top=(!this.scope)?this.factor:0;
      g.node.position.lerpVectors(g.base,g.base.clone().addScaledVector(g.axis,this.scale*.90),top);
      g.node.visible=!this.isolated||!this.scope||g.id===this.scope||g.children.has(this.scope);
      for(const c of g.children.values()){
        const active=!this.scope||this.scope===g.id||this.scope===c.id;
        const factor=this.exempt.has(c.id)?0:(active?this.factor*(this.scope?1:.42):0);
        c.node.position.lerpVectors(c.base,c.base.clone().addScaledVector(c.axis,this.scale*.55),factor);
        c.node.visible=g.node.visible&&(!this.isolated||!this.scope||this.scope===g.id||this.scope===c.id);
      }
    }
    this.root.updateMatrixWorld(true);
    this.emit();
  }
  setExplodeFactor(factor){this.factor=clamp(factor);this.apply();return this.getState();}
  setScope(id=null,{isolate=false}={}){
    if(id&&!this.groups.has(id)&&!this.components.has(id))throw Error('Unknown assembly: '+id);
    this.scope=id||null;this.isolated=Boolean(isolate);this.apply();return this.getState();
  }
  getState(){return {explodeFactor:this.factor,scope:this.scope,isolated:this.isolated,assemblies:[...this.groups].map(([id,g])=>({id,components:[...g.children].map(([key,c])=>({id:key,label:c.label}))}))};}
  onChange(listener){this.listeners.add(listener);return ()=>this.listeners.delete(listener)}
  emit(){const value=this.getState();for(const l of this.listeners)l(value)}
  triggerAlert({system,severity='warning',metric=null,value=null}={}){
    if(!system||(!this.groups.has(system)&&!this.components.has(system)))return {handled:false,reason:'Assembly not present'};
    this.setScope(system,{isolate:true});this.setExplodeFactor(Math.max(.65,this.factor));
    return {handled:true,system,severity,metric,value,state:this.getState()};
  }
  reset(){this.scope=null;this.isolated=false;this.setExplodeFactor(0);}
}
