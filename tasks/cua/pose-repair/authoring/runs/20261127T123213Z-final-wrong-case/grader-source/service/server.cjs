const http=require('node:http'), fs=require('node:fs');
const {P,observations}=require('./model.cjs');
const evidence=process.env.EVIDENCE_DIR||'/service-evidence';
fs.mkdirSync(evidence,{recursive:true});
const log=evidence+'/ledger.jsonl', counts={a:0,b:0,c:0};
// Persistent counters are reconstructed after service restarts; no reset API.
if(fs.existsSync(log)) for(const line of fs.readFileSync(log,'utf8').trim().split('\n').filter(Boolean)) {const r=JSON.parse(line); if(r.kind==='query') counts[r.case]++;}
function record(r) {fs.appendFileSync(log,JSON.stringify(r)+'\n');}
http.createServer(async(req,res)=>{
 let status=200, body;
 try {
  if(req.method==='GET'&&req.url==='/health') body={ready:true};
  else if(req.method==='GET'&&req.url==='/targets') body=Object.fromEntries(['a','b','c'].map(k=>[k,observations(P.targets[k])]));
  else if(req.method==='POST'&&req.url==='/query') {
   let data=''; for await (const chunk of req) {data+=chunk; if(data.length>8192) throw Error('payload too large');}
   const d=JSON.parse(data), k=d.case;
   if(!Object.hasOwn(counts,k)) throw Error('unknown case');
   counts[k]++; // Rejected controls and over-budget calls count too.
   const legal=Array.isArray(d.controls)&&d.controls.length===24&&d.controls.every(x=>typeof x==='number'&&Number.isFinite(x)&&Math.abs(x)<=1);
   const accepted=legal&&counts[k]<=1200;
   record({kind:'query',case:k,index:counts[k],accepted,controls:legal?d.controls:null});
   if(!accepted) {status=422;body={error:'invalid controls or exhausted budget',queries:counts[k]};}
   else body={observations:observations(d.controls),queries:counts[k]};
  } else {record({kind:'denied',path:req.url,method:req.method});status=403;body={error:'public API only'};}
 } catch(e) {status=400;body={error:String(e.message)};}
 res.writeHead(status,{'Content-Type':'application/json','Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'Content-Type'});res.end(JSON.stringify(body));
}).listen(Number(process.env.PORT||8090),'0.0.0.0');
