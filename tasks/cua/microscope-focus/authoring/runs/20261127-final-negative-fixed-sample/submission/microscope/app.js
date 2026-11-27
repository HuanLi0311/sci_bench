import * as THREE from './vendor/three.module.js';
import {OrbitControls} from './vendor/OrbitControls.js';
import {compute} from './optics.js';
const initial={schemaVersion:1,units:'mm',assembly:{body:[55,60,0],tube:[0,80,0],objective:[0,0,0],eyepiece:[0,160,0],stage:[0,-4.12,0]},settings:[{id:'a',stageOffset:0,objectiveOffset:0,eyepieceOffset:0,sample:'sample_a.png'},{id:'b',stageOffset:-0.04,objectiveOffset:0,eyepieceOffset:1,sample:'sample_b.png'},{id:'c',stageOffset:-0.08,objectiveOffset:0,eyepieceOffset:-2,sample:'sample_a.png'}]};
let state=structuredClone(initial),current=structuredClone(initial.settings[0]),result;
const scene=new THREE.Scene(); scene.background=new THREE.Color('#e8edf2');
const camera=new THREE.PerspectiveCamera(40,1,0.1,4000); camera.position.set(300,175,390);
const renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});renderer.setPixelRatio(1);
document.querySelector('#viewport').append(renderer.domElement);
const controls=new OrbitControls(camera,renderer.domElement);controls.target.set(15,65,0);controls.update();
scene.add(new THREE.HemisphereLight(0xffffff,0x526477,2));const light=new THREE.DirectionalLight(0xffffff,3);light.position.set(100,200,150);scene.add(light);
const metal=new THREE.MeshStandardMaterial({color:0x31516c,metalness:.55,roughness:.3});
const lensmat=new THREE.MeshStandardMaterial({color:0x60c7d5,transparent:true,opacity:.58,metalness:.1,roughness:.12});
const group=new THREE.Group();group.name='microscope';scene.add(group);
function part(name,geometry,material=metal,parent=group){const mesh=new THREE.Mesh(geometry,material);mesh.name=name;parent.add(mesh);return mesh;}
const body=part('body',new THREE.BoxGeometry(12,110,28));
part('arm',new THREE.BoxGeometry(56,10,24),metal,body).position.set(-28,50,0);
part('stage_bracket',new THREE.BoxGeometry(22,6,18),metal,body).position.set(-12,-63,0);
part('base',new THREE.BoxGeometry(115,8,90)).position.set(25,-30,0);
const tube=part('tube',new THREE.CylinderGeometry(9,9,142,40,1,true),new THREE.MeshStandardMaterial({color:0x6d8595,transparent:true,opacity:.3,side:THREE.DoubleSide}));
const stage=part('stage',new THREE.BoxGeometry(75,2,55));
const objective=part('objective',new THREE.CylinderGeometry(7,7,1,48),lensmat);
const eyepiece=part('eyepiece',new THREE.CylinderGeometry(12,12,2,48),lensmat);
const specimen=part('specimen',new THREE.PlaneGeometry(22,18),new THREE.MeshBasicMaterial({color:0xffbf55,side:THREE.DoubleSide}),stage);specimen.rotation.x=-Math.PI/2;specimen.position.y=1.02;
const rays=new THREE.Group();rays.name='rays';scene.add(rays);
function line(name,pts,virtual=false){const g=new THREE.BufferGeometry().setFromPoints(pts.map(p=>new THREE.Vector3(...p)));const m=new THREE.LineBasicMaterial({color:virtual?0xd05390:0xee9b22});const l=new THREE.Line(g,m);l.name=name;rays.add(l);}
function raySet(prefix,oy,ly,s,v,m,h){
  if(v===null||Math.abs(v)>1200)return;
  for(let i=0;i<2;i++){
    const x=i===0?h:0, iy=ly+v, ih=h*m;
    const distance=Math.min(Math.abs(v),200);
    line(prefix+'_'+i,[[h,oy,0],[x,ly,0],[x+(ih-x)*distance/v,ly+distance,0]]);
    if(v<0)line(prefix+'_virtual_'+i,[[x,ly,0],[ih,iy,0]],true);
  }
}
const canvas=document.querySelector('#image'),ctx=canvas.getContext('2d',{willReadFrequently:true});
let sampleCanvas=document.createElement('canvas');sampleCanvas.width=sampleCanvas.height=1024;
async function setSample(url){const img=new Image();img.src="./assets/sample_a.png";await img.decode();sampleCanvas.getContext('2d').clearRect(0,0,1024,1024);sampleCanvas.getContext('2d').drawImage(img,0,0,1024,1024);drawImage();}
function drawImage(){
  ctx.fillStyle='#101820';ctx.fillRect(0,0,1280,720);
  if(result.total===null||Math.abs(result.total)>1e5){ctx.fillStyle='white';ctx.font='28px sans-serif';ctx.fillText(result.objective.kind==='infinity'?'Objective image at infinity':'No finite converging image',60,360);return;}
  const scale=Math.abs(result.total)*0.006,w=1024*scale,h=w;
  ctx.save();ctx.translate(640,360);if(result.total<0)ctx.rotate(Math.PI);ctx.imageSmoothingEnabled=false;ctx.drawImage(sampleCanvas,-w/2,-h/2,w,h);ctx.restore();
}
function refresh(){
  for(const n of ['body','tube','objective','eyepiece','stage'])scene.getObjectByName(n).position.fromArray(state.assembly[n]);
  stage.position.y+=current.stageOffset;objective.position.y+=current.objectiveOffset;eyepiece.position.y+=current.eyepieceOffset;
  scene.updateMatrixWorld(true);
  result=compute(stage.getWorldPosition(new THREE.Vector3()).y,objective.getWorldPosition(new THREE.Vector3()).y,eyepiece.getWorldPosition(new THREE.Vector3()).y);
  for(const r of [...rays.children]){r.geometry.dispose();r.material.dispose();rays.remove(r);}
  raySet('objective',stage.position.y,objective.position.y,result.objective.s,result.objective.v,result.objective.m,.05);
  if(result.objective.v!==null)raySet('eyepiece',objective.position.y+result.objective.v,eyepiece.position.y,result.eyepiece.s,result.eyepiece.v,result.eyepiece.m,.05*result.objective.m);
  drawImage();document.querySelector('#readout').textContent=JSON.stringify(result,null,2);renderer.render(scene,camera);
}
async function applyState(s,index=0){state=structuredClone(s);current=structuredClone(state.settings[index]);refresh();await setSample('./assets/'+current.sample);return result;}
async function setControls(patch){Object.assign(current,patch);refresh();return result;}
function serialize(){const s=structuredClone(state);s.settings[0]=structuredClone(current);return s;}
function reset(){return applyState(initial);}
function resize(){const e=document.querySelector('#viewport');renderer.setSize(e.clientWidth,e.clientHeight);camera.aspect=e.clientWidth/e.clientHeight;camera.updateProjectionMatrix();renderer.render(scene,camera);}
window.addEventListener('resize',resize);controls.addEventListener('change',()=>renderer.render(scene,camera));resize();
window.microscope={scene,renderer,applyState,setControls,setSample,serialize,reset,get optics(){return result;}};
for(const [id,key] of [['focus','stageOffset'],['eye','eyepieceOffset']])document.getElementById(id).oninput=async e=>{await setControls({[key]:+e.target.value});};
document.querySelector('#sample').onchange=e=>setSample('./assets/'+e.target.value);
document.querySelector('#preset').onchange=e=>applyState(state,+e.target.value);
document.querySelector('#save').onclick=()=>{localStorage.setItem('microscope-state',JSON.stringify(serialize()));const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(serialize(),null,2)],{type:'application/json'}));a.download='state.json';a.click();};
document.querySelector('#reload').onclick=()=>applyState(JSON.parse(localStorage.getItem('microscope-state')||JSON.stringify(initial)));
document.querySelector('#reset').onclick=reset;
document.querySelector('#load').onchange=async e=>applyState(JSON.parse(await e.target.files[0].text()));
await applyState(initial);window.ready=true;
