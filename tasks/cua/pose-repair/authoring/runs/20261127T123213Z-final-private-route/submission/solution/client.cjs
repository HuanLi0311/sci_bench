const http=require('node:http');
const base=process.env.POSE_SERVICE||'http://pose-service:8090';
function request(path,data) {return new Promise((resolve,reject)=>{
 const b=data?JSON.stringify(data):null;
 const req=http.request(base+path,{method:b?'POST':'GET',headers:b?{'Content-Type':'application/json','Content-Length':Buffer.byteLength(b)}:{}},res=>{let s='';res.on('data',c=>s+=c);res.on('end',()=>{try{const r=JSON.parse(s);res.statusCode===200?resolve(r):reject(Error(s));}catch(e){reject(e);}});});
 req.setTimeout(10000,()=>req.destroy(Error('service timeout')));req.on('error',reject);req.end(b);
});}
module.exports={targets:()=>request('/targets'),query:(k,u)=>request('/query',{case:k,controls:u})};
