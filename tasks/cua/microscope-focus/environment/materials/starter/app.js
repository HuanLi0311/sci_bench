import * as THREE from './vendor/three.module.js';
import {OrbitControls} from './vendor/OrbitControls.js';
const scene=new THREE.Scene();scene.background=new THREE.Color('#e8edf2');
const camera=new THREE.PerspectiveCamera(45,1.5,.1,3000);camera.position.set(250,180,350);
const renderer=new THREE.WebGLRenderer({antialias:true});renderer.setSize(960,640);document.body.append(renderer.domElement);
scene.add(new THREE.HemisphereLight(0xffffff,0x526477,2));scene.add(new THREE.AxesHelper(100));
const controls=new OrbitControls(camera,renderer.domElement);controls.target.set(0,60,0);controls.update();
renderer.setAnimationLoop(()=>renderer.render(scene,camera));
// TODO: assembly, real focus motion, two-stage optics, rays, samples, persistence,
// and window.microscope interface from ../SPEC.md. No solution is supplied here.
