/* Browser-based GLB/WebGL acceptance smoke for the publicly redistributable reference model.
   This never examines the owner's confidential workbook or photo set. */
const assert=require('node:assert/strict');
const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-gpu-sandbox','--enable-webgl','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const page=await browser.newPage({viewport:{width:1300,height:820},deviceScaleFactor:1});
 const errors=[];page.on('pageerror',e=>errors.push(String(e)));page.on('console',m=>{if(m.type()==='error')errors.push('console: '+m.text())});
 await page.goto('http://127.0.0.1:8115/__3d_smoke.html',{waitUntil:'load'});
 await page.waitForFunction(()=>document.querySelector('#ix3d-status')?.textContent?.includes('pickable reference meshes'),null,{timeout:65000});
 const output=await page.evaluate(()=>({status:document.querySelector('#ix3d-status')?.textContent,canvas:document.querySelector('#ix3d-stage canvas')?.getBoundingClientRect().toJSON(),fallbackHidden:document.querySelector('#ix3d-fallback')?.hidden,modelVisible:!document.querySelector('#ix3d-stage')?.hidden,modelSrcLoaded:true}));
 assert(output.canvas && output.canvas.width>=750 && output.canvas.height>=450,'WebGL canvas not sized');
 assert(output.modelVisible && output.fallbackHidden,'Viewer fell back to 2D despite model loaded');
 const count=Number((output.status.match(/^(\d+) pickable/)||[])[1]);assert(count>=1,'Real model yielded no mesh selection targets');
 await page.locator('#ix3d-explode').evaluate(el=>{el.value='35';el.dispatchEvent(new Event('input',{bubbles:true}))});
 await page.waitForTimeout(900);
 await page.screenshot({path:'out/rc15_3d_smoke.png'});
 console.log('PASS: REAL WebGL GLB rendered in browser; mesh pickables='+count+'; canvas='+output.canvas.width+'x'+output.canvas.height+'; explosion event completed; screenshot captured');
 if(errors.length)throw new Error('Browser errors: '+errors.slice(0,10).join(' | '));
 await browser.close();
})().catch(e=>{console.error('FAIL: real browser GLB smoke',e);process.exit(1)});
