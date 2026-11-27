// Numerical Gauss-Newton using only budgeted 2D public observations.
const client=require('./client.cjs'), fs=require('node:fs');
const dot=(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0);
function solve(A,b) {
 const m=A.map((r,i)=>[...r,b[i]]), n=b.length;
 for(let i=0;i<n;i++) {let p=i;for(let j=i+1;j<n;j++)if(Math.abs(m[j][i])>Math.abs(m[p][i]))p=j;[m[i],m[p]]=[m[p],m[i]];const d=m[i][i];if(Math.abs(d)<1e-12)throw Error('singular');for(let k=i;k<=n;k++)m[i][k]/=d;for(let j=0;j<n;j++)if(j!==i){const v=m[j][i];for(let k=i;k<=n;k++)m[j][k]-=v*m[i][k];}}
 return m.map(r=>r[n]);
}
async function fit(k,target) {
 let u=Array(24).fill(0), count=0;
 async function obs(x) {const r=await client.query(k,x);count=r.queries;return r.observations;}
 for(let iter=0;iter<22;iter++) {
  const y=await obs(u), residual=y.map((v,i)=>target[i]-v);
  if(Math.sqrt(dot(residual,residual)/residual.length)<0.015)break;
  const J=[];for(let j=0;j<24;j++){let v=u.slice(),h=u[j]<0.999?0.0001:-0.0001;v[j]+=h;const z=await obs(v);J[j]=z.map((x,i)=>(x-y[i])/h);}
  const A=J.map((a,i)=>J.map((b,j)=>dot(a,b)+(i===j?0.02:0))), b=J.map(a=>dot(a,residual));
  const delta=solve(A,b), err=dot(residual,residual);
  for(const alpha of [1,0.5,0.25,0.125]) {const v=u.map((x,j)=>Math.max(-1,Math.min(1,x+alpha*delta[j]))), z=await obs(v), r=z.map((x,i)=>target[i]-x);if(dot(r,r)<err){u=v;break;}}
 }
 return {controls:u,queries:count};
}
async function main(){const dest=process.argv[2]||'/app/out';fs.mkdirSync(dest+'/solution',{recursive:true});const t=await client.targets(), report={};for(const k of ['a','b','c']){const r=await fit(k,t[k]);fs.writeFileSync(`${dest}/controls_case_${k}.json`,JSON.stringify(r.controls));report[k]=r.queries;}if(__filename!==dest+'/solution/fitter.cjs')fs.copyFileSync(__filename,dest+'/solution/fitter.cjs');if(require.resolve('./client.cjs')!==dest+'/solution/client.cjs')fs.copyFileSync(require.resolve('./client.cjs'),dest+'/solution/client.cjs');fs.writeFileSync(dest+'/replay.json',JSON.stringify({schemaVersion:1,scene:'avatar.glb',cases:['a','b','c'].map(k=>`controls_case_${k}.json`)}));fs.writeFileSync(dest+'/report.md',`Run: node /app/out/solution/fitter.cjs /app/out\nMethod: finite-difference damped Gauss-Newton on three-view joint and orientation markers.\nQueries: ${JSON.stringify(report)}\n`);fs.writeFileSync(dest+'/query_counts.json',JSON.stringify(report));}
if(require.main===module)main().catch(e=>{console.error(e);process.exit(1)});
module.exports={fit};
