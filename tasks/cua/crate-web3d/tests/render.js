/**
 * Deterministic re-render of a .glb from one of its cameras.
 *
 *   node render.js --glb /path/scene.glb --camera cam_front \
 *                  --out /tmp/x.png [--w 800] [--h 600] [--rotate lid_hinge:60]
 *
 * Serves three.js, the viewer page and the .glb from a throwaway local server,
 * renders in Chromium (SwiftShader), screenshots the canvas. Same image twice
 * on the same machine is byte-identical, which is what the SSIM gates rely on.
 */
const http = require('http');
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const THREE_ROOT = '/usr/local/lib/node_modules/three';
const HERE = __dirname;

function arg(name, def) {
  const i = process.argv.indexOf('--' + name);
  return i > 0 ? process.argv[i + 1] : def;
}

const GLB = arg('glb');
const CAMERA = arg('camera', 'cam_front');
const OUT = arg('out', '/tmp/render.png');
const W = +arg('w', 800);
const H = +arg('h', 600);
const ROTATE = arg('rotate', '');

function serve() {
  return new Promise((resolve) => {
    const srv = http.createServer((req, res) => {
      const u = new URL(req.url, 'http://x');
      const send = (file, type) => fs.readFile(file, (e, d) => {
        if (e) { res.writeHead(404); res.end(); return; }
        res.writeHead(200, { 'Content-Type': type });
        res.end(d);
      });
      if (u.pathname === '/viewer.html') return send(path.join(HERE, 'viewer.html'), 'text/html');
      if (u.pathname === '/vendor/three.module.js') return send(path.join(THREE_ROOT, 'build/three.module.js'), 'text/javascript');
      if (u.pathname === '/vendor/GLTFLoader.js') return send(path.join(THREE_ROOT, 'examples/jsm/loaders/GLTFLoader.js'), 'text/javascript');
      if (u.pathname === '/scene.glb') return send(GLB, 'model/gltf-binary');
      res.writeHead(404); res.end();
    });
    srv.listen(0, '127.0.0.1', () => resolve(srv));
  });
}

(async () => {
  const srv = await serve();
  const port = srv.address().port;
  const q = new URLSearchParams({ scene: '/scene.glb', camera: CAMERA, w: W, h: H });
  if (ROTATE) q.set('rotate', ROTATE);

  const browser = await chromium.launch({
    args: ['--enable-unsafe-swiftshader', '--use-gl=angle', '--use-angle=swiftshader'],
  });
  const page = await browser.newPage({ viewport: { width: W, height: H } });
  await page.goto(`http://127.0.0.1:${port}/viewer.html?${q}`);
  await page.waitForFunction('window.__done === true', null, { timeout: 180000 });
  const err = await page.evaluate('window.__error || null');
  const cam = await page.evaluate('window.__camera || null');
  await page.locator('canvas').screenshot({ path: OUT });
  await browser.close();
  srv.close();
  console.log(JSON.stringify({ out: OUT, camera: cam, error: err }));
  if (err) process.exit(1);
})();
