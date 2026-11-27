/**
 * Minimal in-browser 3D editor for the crate-web3d task.
 *
 * Deliberately small: an object list, numeric transform fields, box/cylinder
 * primitives, a camera, an environment light and a glTF export button. Every
 * edit is a number typed into a field, so millimetre work is possible without
 * pixel dragging.
 *
 * Served by server.js; the browser loads /vendor/three.module.js.
 */
import * as THREE from '/vendor/three.module.js';
import { GLTFExporter } from '/vendor/GLTFExporter.js';

const W = 1280, H = 760;

const renderer = new THREE.WebGLRenderer({ antialias: false, preserveDrawingBuffer: true });
renderer.setPixelRatio(1);
renderer.setSize(W, H);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;
document.getElementById('viewport').appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x1d1f22);
const camera = new THREE.PerspectiveCamera(35, W / H, 0.01, 100);
camera.position.set(1.13, -1.13, 0.90);
camera.lookAt(0, 0, 0.32);

const hemi = new THREE.HemisphereLight(0xffffff, 0x444444, 1.5);
scene.add(hemi);
const key = new THREE.DirectionalLight(0xffffff, 2.2);
key.position.set(2, -2, 4);
key.castShadow = true;
key.shadow.mapSize.set(1024, 1024);
scene.add(key);
const floor = new THREE.Mesh(new THREE.PlaneGeometry(8, 8),
  new THREE.MeshStandardMaterial({ color: 0x33363a, roughness: 0.9 }));
floor.rotation.x = -Math.PI / 2;
floor.receiveShadow = true;
scene.add(floor);

const state = { selected: null, nextId: 1 };
const objects = [];

function refreshOutliner() {
  const list = document.getElementById('outliner');
  list.innerHTML = '';
  for (const ob of objects) {
    const row = document.createElement('div');
    row.className = 'row' + (ob === state.selected ? ' sel' : '');
    row.textContent = ob.name;
    row.onclick = () => select(ob);
    list.appendChild(row);
  }
}

const FIELDS = ['px', 'py', 'pz', 'sx', 'sy', 'sz', 'rx', 'ry', 'rz'];

function select(ob) {
  state.selected = ob;
  refreshOutliner();
  const form = document.getElementById('props');
  form.style.display = ob ? 'block' : 'none';
  if (!ob) return;
  document.getElementById('nameField').value = ob.name;
  const v = ob.userData.dims || [1, 1, 1];
  const d = document.getElementById('dims');
  d.textContent = v.map(x => (x * 1000).toFixed(1)).join(' x ') + ' mm';
  document.getElementById('px').value = (ob.position.x * 1000).toFixed(3);
  document.getElementById('py').value = (ob.position.y * 1000).toFixed(3);
  document.getElementById('pz').value = (ob.position.z * 1000).toFixed(3);
  document.getElementById('sx').value = (ob.scale.x * 1000).toFixed(3);
  document.getElementById('sy').value = (ob.scale.y * 1000).toFixed(3);
  document.getElementById('sz').value = (ob.scale.z * 1000).toFixed(3);
  document.getElementById('rx').value = THREE.MathUtils.radToDeg(ob.rotation.x).toFixed(2);
  document.getElementById('ry').value = THREE.MathUtils.radToDeg(ob.rotation.y).toFixed(2);
  document.getElementById('rz').value = THREE.MathUtils.radToDeg(ob.rotation.z).toFixed(2);
}

function apply() {
  const ob = state.selected;
  if (!ob) return;
  ob.name = document.getElementById('nameField').value.trim() || ob.name;
  ob.position.set(+document.getElementById('px').value / 1000,
                  +document.getElementById('py').value / 1000,
                  +document.getElementById('pz').value / 1000);
  ob.scale.set(+document.getElementById('sx').value / 1000,
               +document.getElementById('sy').value / 1000,
               +document.getElementById('sz').value / 1000);
  ob.rotation.set(THREE.MathUtils.degToRad(+document.getElementById('rx').value),
                  THREE.MathUtils.degToRad(+document.getElementById('ry').value),
                  THREE.MathUtils.degToRad(+document.getElementById('rz').value));
  refreshOutliner();
  render();
}

function addBox(dims) {
  const geo = new THREE.BoxGeometry(1, 1, 1);
  const mat = new THREE.MeshStandardMaterial({ color: 0x8a5a32, roughness: 0.6 });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.scale.set(dims[0], dims[1], dims[2]);
  mesh.userData.dims = dims.slice();
  mesh.castShadow = mesh.receiveShadow = true;
  mesh.name = 'box_' + String(state.nextId++).padStart(2, '0');
  scene.add(mesh);
  objects.push(mesh);
  select(mesh);
  render();
  return mesh;
}

function render() {
  renderer.render(scene, camera);
  document.getElementById('status').textContent =
    objects.length + ' objects | ' + (state.selected ? state.selected.name : 'nothing selected');
}

document.getElementById('addBox').onclick = () => addBox([0.1, 0.1, 0.1]);
document.getElementById('apply').onclick = apply;
document.getElementById('del').onclick = () => {
  if (!state.selected) return;
  scene.remove(state.selected);
  objects.splice(objects.indexOf(state.selected), 1);
  select(null);
  render();
};

document.getElementById('export').onclick = async () => {
  const exporter = new GLTFExporter();
  const payload = await exporter.parseAsync(scene, { binary: true, embedImages: true });
  const blob = new Blob([payload], { type: 'model/gltf-binary' });
  const res = await fetch('/save?name=scene.glb', { method: 'POST', body: blob });
  document.getElementById('status').textContent = res.ok
    ? 'exported /app/out/scene.glb'
    : 'export failed';
};

// deterministic render hook for the verifier and for scripted solving
window.__editor = {
  scene, camera, renderer, objects,
  addBox, apply, select, render,
  setCamera(p, t) {
    camera.position.set(p[0], p[1], p[2]);
    camera.lookAt(t[0], t[1], t[2]);
    render();
  },
};

render();
window.__ready = true;
