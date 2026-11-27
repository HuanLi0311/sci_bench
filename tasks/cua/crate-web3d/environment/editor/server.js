/**
 * Static server for the editor plus two endpoints:
 *   POST /save?name=scene.glb   writes the request body into /app/out
 *   GET  /files/<name>          serves a file from /app/out
 *
 * No framework, no dependencies beyond Node's standard library.
 */
const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 8080;
const ROOT = '/app';
const EDITOR = path.join(ROOT, 'editor');
const OUT = path.join(ROOT, 'out');
const THREE_ROOT = '/usr/local/lib/node_modules/three';

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.glb': 'model/gltf-binary',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.json': 'application/json',
};

function send(res, code, body, type = 'text/plain; charset=utf-8') {
  res.writeHead(code, { 'Content-Type': type });
  res.end(body);
}

function serveFile(res, file) {
  fs.readFile(file, (err, data) => {
    if (err) return send(res, 404, 'not found');
    send(res, 200, data, MIME[path.extname(file)] || 'application/octet-stream');
  });
}

function safeJoin(base, rel) {
  const p = path.normalize(path.join(base, rel));
  return p.startsWith(base) ? p : null;
}

http.createServer((req, res) => {
  const url = new URL(req.url, 'http://localhost');

  if (req.method === 'POST' && url.pathname === '/save') {
    const name = path.basename(url.searchParams.get('name') || 'scene.glb');
    const chunks = [];
    req.on('data', c => chunks.push(c));
    req.on('end', () => {
      fs.mkdirSync(OUT, { recursive: true });
      fs.writeFileSync(path.join(OUT, name), Buffer.concat(chunks));
      send(res, 200, 'ok');
    });
    return;
  }

  if (url.pathname.startsWith('/vendor/')) {
    const name = url.pathname.slice('/vendor/'.length);
    const file = name.startsWith('GLTFExporter')
      ? path.join(THREE_ROOT, 'examples/jsm/exporters/GLTFExporter.js')
      : path.join(THREE_ROOT, 'build/three.module.js');
    return serveFile(res, file);
  }

  if (url.pathname.startsWith('/files/')) {
    const file = safeJoin(OUT, url.pathname.slice('/files/'.length));
    return file ? serveFile(res, file) : send(res, 403, 'nope');
  }

  if (url.pathname.startsWith('/materials/')) {
    const file = safeJoin(path.join(ROOT, 'materials'), url.pathname.slice('/materials/'.length));
    return file ? serveFile(res, file) : send(res, 403, 'nope');
  }

  const rel = url.pathname === '/' ? 'index.html' : url.pathname.slice(1);
  const file = safeJoin(EDITOR, rel);
  return file ? serveFile(res, file) : send(res, 403, 'nope');
}).listen(PORT, '0.0.0.0', () => {
  console.log('editor on http://0.0.0.0:' + PORT);
});
