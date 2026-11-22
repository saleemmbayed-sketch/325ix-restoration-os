/* Local standard-library smoke for parametric hierarchy. No npm or cloud needed.
 * The runtime includes a local MIT Three.js copy in vendor/; this test rewrites
 * the browser-absolute import to that exact local copy in a temporary ESM file.
 */
import assert from 'node:assert/strict';
import {readFile, writeFile, mkdtemp, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join, dirname, resolve} from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
const BASE=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const threeUrl=pathToFileURL(join(BASE,'vendor/three/build/three.module.js')).href;
const source=(await readFile(join(BASE,'explosion-rig.js'),'utf8'))
 .replace("from '/vendor/three/build/three.module.js'", `from '${threeUrl}'`);
const tmp=await mkdtemp(join(tmpdir(),'ix-rig-test-'));
try{
 const rigFile=join(tmp,'explosion-rig.mjs');await writeFile(rigFile,source);
 const THREE=await import(threeUrl);
 const {ExplosionRig}=await import(pathToFileURL(rigFile).href);
 const root=new THREE.Group();root.name='BMW_E30';
 const components=[
  ['bonnet','bodywork',0,1,1.8], ['valve_cover','engine',0,.5,.2],
  ['radiator','radiator',0,.2,1.6],['strut_tube','front_axle',-1,-.3,.9],
  ['transfer_case','transfer_box_electric_gearbox',0,-.8,-.4],
  ['differential','rear_axle',0,-.7,-1.4]
 ];
 const meshes=[];
 for(const [id,_system,x,y,z] of components){
  for(let i=0;i<3;i++){
   const m=new THREE.Mesh(new THREE.BoxGeometry(.2,.2,.2),new THREE.MeshStandardMaterial());
   m.name=`MX:${id}:${i}`;m.position.set(x+i*.01,y,z);
   root.add(m);meshes.push(m);
  }
 }
 root.updateMatrixWorld(true);
 const original=meshes.map(x=>x.getWorldPosition(new THREE.Vector3()));
 const metadata={slug:'ix_m20_engine_bay',components:components.map(([id,system])=>({id,system,label:id}))};
 const rig=new ExplosionRig(root,metadata);
 assert.equal(rig.components.size,6,'Semantic fragments must share component pivots');
 assert.equal(rig.groups.size,5,'All six parts should be in five named assemblies');
 for(let i=0;i<meshes.length;i++)assert.ok(meshes[i].getWorldPosition(new THREE.Vector3()).distanceTo(original[i])<1e-5,'Initial position drift');
 for(const factor of [0,.2,.5,1,.5,0,1,0])rig.setExplodeFactor(factor);
 for(let i=0;i<meshes.length;i++)assert.ok(meshes[i].getWorldPosition(new THREE.Vector3()).distanceTo(original[i])<1e-5,'Reset drift');
 rig.setScope('Cooling',{isolate:true});rig.setExplodeFactor(.7);
 assert.equal(rig.groups.get('Engine_Assembly').node.visible,false);
 assert.equal(rig.groups.get('Cooling').node.visible,true);
 const event=rig.triggerAlert({system:'Drivetrain',metric:'vibration',value:3.1});
 assert.equal(event.handled,true);assert.equal(rig.scope,'Drivetrain');
 let notified=0;const off=rig.onChange(()=>notified++);rig.setExplodeFactor(.3);off();assert.equal(notified,1);
 rig.reset();assert.equal(rig.factor,0);assert.equal(rig.scope,null);
 for(let i=0;i<meshes.length;i++)assert.ok(meshes[i].getWorldPosition(new THREE.Vector3()).distanceTo(original[i])<1e-5,'Post-alert reset drift');
 console.log('PASS RC20: 5 parent assemblies, 6 components / 18 meshes, normalized 0/.2/.5/1 LERP, isolate, telemetry, subscription, zero-drift reset');
}finally{await rm(tmp,{recursive:true,force:true})}
