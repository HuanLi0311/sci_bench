import {chromium} from '/opt/runtime/node_modules/playwright/index.mjs';
import fs from 'node:fs';
const request=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const browser=await chromium.launch({channel:'chromium',headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-dev-shm-usage']});
// Trusted cold-start probe. A failed browser/WebGL runtime is infrastructure.
const test=await browser.newPage();await test.goto('http://127.0.0.1:8090/__health');
if(!await test.evaluate(()=>!!document.createElement('canvas').getContext('webgl2')))throw Error('INFRA: WebGL2 unavailable');await test.close();
const all=[];
for(const job of request.jobs){
 const context=await browser.newContext({viewport:{width:1600,height:1000},serviceWorkers:'block'}),page=await context.newPage();const external=[],errors=[];
 await context.route('**/*',route=>{const u=new URL(route.request().url());if(!['127.0.0.1','localhost'].includes(u.hostname)){external.push(u.href);return route.abort();}return route.continue();});
 page.on('pageerror',e=>errors.push(String(e)));
 try{
  await page.goto(request.url,{timeout:12000,waitUntil:'networkidle'});
  await page.waitForFunction(()=>!!window.microscope,{timeout:5000});
  await page.evaluate(async ({s,index,patch,sample})=>{await window.microscope.applyState(s,index);if(patch)await window.microscope.setControls(patch);if(sample)await window.microscope.setSample(sample);}, {s:request.state,...job});
  const snapshot=()=>page.evaluate(()=>{
    const a=window.microscope;a.scene.updateMatrixWorld(true);
    const parts={};for(const n of ['body','tube','stage','objective','eyepiece']){
     const o=a.scene.getObjectByName(n);if(!o){parts[n]=null;continue;}
     const e=o.matrixWorld.elements;const p=[e[12],e[13],e[14]];o.geometry?.computeBoundingBox();const b=o.geometry?.boundingBox;
     parts[n]={position:p,rotation:o.rotation.toArray().slice(0,3),mesh:!!o.isMesh,vertices:o.geometry?.attributes.position.count||0,bounds:b?[b.min.toArray(),b.max.toArray()]:null,parent:o.parent?.name,visible:o.visible};
    }
    const rays=[];a.scene.traverse(o=>{if(o.isLine&&/^(objective|eyepiece)_/.test(o.name)){const p=o.geometry.attributes.position,pts=[];for(let i=0;i<p.count;i++){const e=o.matrixWorld.elements,x=p.getX(i),y=p.getY(i),z=p.getZ(i);pts.push([e[0]*x+e[4]*y+e[8]*z+e[12],e[1]*x+e[5]*y+e[9]*z+e[13],e[2]*x+e[6]*y+e[10]*z+e[14]]);}rays.push({name:o.name,points:pts});}});
    return {parts,rays,optics:structuredClone(a.optics),image:document.querySelector('#image').toDataURL('image/png'),rendered:a.renderer?.info.render.triangles||0};
  });
  const value=await snapshot();
  if(job.persistence){await page.evaluate(async()=>{const a=window.microscope;const saved=JSON.stringify(a.serialize());await a.setControls({stageOffset:.5});await a.applyState(JSON.parse(saved),0);});value.restored=await snapshot();await page.evaluate(()=>window.microscope.reset());value.reset=await snapshot();}
  all.push({job:job.name,...value,external,errors});
 }catch(e){all.push({job:job.name,error:String(e),external,errors});}
 await context.close();
}
await browser.close();fs.writeFileSync(process.argv[3],JSON.stringify(all));
