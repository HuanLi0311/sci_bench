/**
 * Render one camera of a .glb.
 *
 *   node render_views.js <glb> <cameraName> <outPng> [width] [height] [rotate]
 *
 * Same viewer and same Chromium/SwiftShader settings as the verifier, so the
 * reference renders and the anti-cheat re-renders are comparable.
 */
const http = require('http');
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const THREE_ROOT = '/usr/local/lib/node_modules/three';
const HERE = __dirname;

const [, , GLB, CAMERA, OUT, W = '1200', H = '900', ROTATE = ''] = process.argv;

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
  const q = new URLSearchParams({ scene: '/scene.glb', camera: CAMERA, w: W, h: H });
  if (ROTATE) q.set('rotate', ROTATE);
  const browser = await chromium.launch({
    args: ['--enable-unsafe-swiftshader', '--use-gl=angle', '--use-angle=swiftshader'],
  });
  const page = await browser.newPage({ viewport: { width: +W, height: +H } });
  await page.goto(`http://127.0.0.1:${srv.address().port}/viewer.html?${q}`);
  await page.waitForFunction('window.__done === true', null, { timeout: 180000 });
  await page.locator('canvas').screenshot({ path: OUT });
  await browser.close();
  srv.close();
})();
