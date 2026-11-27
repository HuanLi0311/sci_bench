// Static local UI plus an API proxy; private coupling stays in the sidecar.
const http=require('node:http'),fs=require('node:fs'),path=require('node:path');
const root='/app/materials',host=process.env.POSE_SERVICE||'http://pose-service:8090';
http.createServer((req,res)=>{
 if(req.url.startsWith('/api/')){const r=http.request(host+req.url.slice(4),{method:req.method,headers:{'Content-Type':'application/json'}},p=>{res.writeHead(p.statusCode,{'Content-Type':'application/json'});p.pipe(res);});r.on('error',()=>{res.writeHead(503);res.end('{"error":"service unavailable"}');});req.pipe(r);return;}
 const filename=path.resolve(root,'.'+decodeURIComponent(req.url==='/'?'/index.html':req.url));if(!filename.startsWith(root+'/')){res.writeHead(403);res.end();return;}
 fs.readFile(filename,(e,b)=>{res.writeHead(e?404:200,{'Content-Type':filename.endsWith('.html')?'text/html':filename.endsWith('.png')?'image/png':'application/octet-stream'});res.end(e?'not found':b);});
}).listen(8080,'0.0.0.0');
