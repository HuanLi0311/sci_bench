import {chromium} from '/opt/runtime/node_modules/playwright/index.mjs';
import fs from 'node:fs';
const b=await chromium.launch({channel:'chromium',args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});const p=await b.newPage();p.on('pageerror',e=>console.log(String(e)));await p.goto('http://127.0.0.1:8081/microscope/');await p.waitForFunction(()=>window.ready);
const landmarks={};
for(const [name,pos] of [['front',[0,65,500]],['side',[500,65,0]],['three_quarter',[350,210,450]]]){
 const data=await p.evaluate(async(pos)=>{const T=await import('./vendor/three.module.js');const a=window.microscope;const cam=new T.OrthographicCamera(-155,155,116.25,-116.25,.1,2000);cam.position.set(...pos);cam.lookAt(0,65,0);a.renderer.setSize(1280,960);a.renderer.render(a.scene,cam);return a.renderer.domElement.toDataURL('image/png');},pos);
 fs.writeFileSync('/refs/'+name+'.png',Buffer.from(data.split(',')[1],'base64'));
 landmarks[name]=await p.evaluate(async(pos)=>{const T=await import('./vendor/three.module.js');const cam=new T.OrthographicCamera(-155,155,116.25,-116.25,.1,2000);cam.position.set(...pos);cam.lookAt(0,65,0);cam.updateMatrixWorld();cam.updateProjectionMatrix();return Object.fromEntries(['body','tube','objective','eyepiece','stage'].map(n=>{const v=window.microscope.scene.getObjectByName(n).getWorldPosition(new T.Vector3()).project(cam);return[n,[(v.x+1)*640,(1-v.y)*480]];}));},pos);
}
fs.writeFileSync('/refs/landmarks.json',JSON.stringify(landmarks));
await b.close();
