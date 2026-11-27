// QA against our own local inspector. No external browser or accounts.
async function main(){
 const tabs=await fetch('http://127.0.0.1:9222/json').then(r=>r.json()),tab=tabs.find(t=>t.url==='http://localhost:8080/');
 if(!tab)throw Error('inspector tab missing');
 const ws=new WebSocket(tab.webSocketDebuggerUrl);await new Promise((r,e)=>{ws.onopen=r;ws.onerror=e;});let serial=0;
 async function evaluate(expression){return new Promise((resolve,reject)=>{const id=++serial;const listener=e=>{const x=JSON.parse(e.data);if(x.id===id){ws.removeEventListener('message',listener);x.error?reject(Error(JSON.stringify(x.error))):resolve(x.result.result.value);}};ws.addEventListener('message',listener);ws.send(JSON.stringify({id,method:'Runtime.evaluate',params:{expression,returnByValue:true,awaitPromise:true}}));});}
 const gl=await evaluate("(()=>{let gl=document.querySelector('canvas').getContext('webgl2');return {webgl:gl.getParameter(gl.VERSION),targets:[...document.images].map(x=>({width:x.naturalWidth,height:x.naturalHeight})),title:document.title};})()");
 if(!gl.webgl.includes('WebGL 2.0')||!gl.targets.every(x=>x.width===1280&&x.height===720))throw Error(JSON.stringify(gl));
 await evaluate("document.getElementById('query').click()");
 let status='';for(let i=0;i<40;i++){status=await evaluate("document.getElementById('status').textContent");if(status.includes('Queries used: 1'))break;await new Promise(r=>setTimeout(r,100));}
 if(!status.includes('Queries used: 1'))throw Error(status);
 console.log(JSON.stringify({...gl,status}));ws.close();
}
main().catch(e=>{console.error(e);process.exit(1);});
