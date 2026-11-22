/* Real WebGL acceptance for 3 original interactive mechanical assemblies.
   Runs only in the existing GitHub asset workflow; no extra runtime library. */
const assert=require('node:assert/strict');
const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-gpu-sandbox','--enable-webgl','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const page=await browser.newPage({viewport:{width:1330,height:800},deviceScaleFactor:1});
 const errors=[];page.on('pageerror',e=>errors.push(String(e)));
 page.on('console',m=>{if(m.type()==='error')errors.push('console: '+m.text())});
 await page.goto('http://127.0.0.1:8115/__mechanical_smoke.html',{waitUntil:'load'});
 await page.waitForFunction(()=>document.querySelector('#ix3d-status')?.textContent?.includes('selectable components'),null,{timeout:60000});
 const initial=await page.evaluate(()=>({status:document.querySelector('#ix3d-status').textContent,canvas:document.querySelector('#ix3d-stage canvas')?.getBoundingClientRect().toJSON(),
  component:window.ixStudio3D?.focusMechanicalComponent('valve_cover')}));
 assert(initial.canvas?.width>=900&&initial.canvas.height>=500,'Engine WebGL canvas not rendered');
 assert(initial.component,'Original GLB node name/picking key was not preserved');
 assert.equal(await page.locator('#selected').innerText(),'valve_cover','Semantic component callback must fire');
 const isolate=await page.evaluate(()=>window.ixStudio3D.isolateMechanicalComponent('intake_runners'));
 assert(isolate,'Isolate must work');
 await page.evaluate(()=>window.ixStudio3D.isolateMechanicalComponent('intake_runners'));
 const bonnet=await page.evaluate(()=>window.ixStudio3D.toggleBonnet());assert(bonnet,'Bonnet hinge must be present and animated');
 await page.waitForTimeout(700);
 await page.screenshot({path:'out/rc19_m20_engine_webgl.png'});
 const axle=await page.evaluate(async()=>{
   const scene=window.mechanicalIndex.scenes[1];const out=await window.ixStudio3D.openMechanical(scene,window.twinData);
   return {...out,picked:window.ixStudio3D.focusMechanicalComponent('strut_tube')};
 });
 assert(axle.components>=14&&axle.picked,'Front axle selectable strut not rendered');
 await page.screenshot({path:'out/rc19_front_axle_webgl.png'});
 const awd=await page.evaluate(async()=>{
   const scene=window.mechanicalIndex.scenes[2];const out=await window.ixStudio3D.openMechanical(scene,window.twinData);
   return {...out,picked:window.ixStudio3D.focusMechanicalComponent('transfer_case')};
 });
 assert(awd.components>=11&&awd.picked,'Transfer-case component not selectable');
 assert.equal(await page.locator('#selected').innerText(),'transfer_case');
 if(errors.length)throw new Error('Browser errors: '+errors.slice(0,8).join(' | '));
 console.log('PASS original WebGL 3D: M20 '+initial.status+'; bonnet animation; mesh isolate/focus; front axle '+axle.pickable+' meshes; AWD '+awd.pickable+' meshes; semantic part IDs');
 await browser.close();
})().catch(e=>{console.error('FAIL mechanical browser smoke',e);process.exit(1)});
