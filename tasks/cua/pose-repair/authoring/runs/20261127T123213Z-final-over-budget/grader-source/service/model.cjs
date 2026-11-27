// Verifier-only coupling. This module is never copied to the main image.
const fs = require('node:fs');
const P = JSON.parse(fs.readFileSync(__dirname+'/fixture.json','utf8'));
const add=(a,b)=>a.map((v,i)=>v+b[i]);
const mul=(a,b)=>a.map(r=>b[0].map((_,j)=>r.reduce((s,v,k)=>s+v*b[k][j],0)));
const mv=(a,b)=>a.map(r=>r.reduce((s,v,i)=>s+v*b[i],0));
function rot([x,y,z]) { const [a,b,c,d,e,f]=[Math.cos(x),Math.sin(x),Math.cos(y),Math.sin(y),Math.cos(z),Math.sin(z)]; return [[e*c,e*d*b-f*a,e*d*a+f*b],[f*c,f*d*b+e*a,f*d*a-e*b],[-d,c*b,c*a]]; }
function pose(u) {
  const q=P.matrix.map((row,i)=>row.reduce((s,v,j)=>s+v*u[j],P.bias[i])+0.12*Math.sin(u[i]));
  const pos=[], matrices=[];
  for(let i=0;i<8;i++) {
    const parent=P.parents[i], local=rot(q.slice(i*3,i*3+3));
    matrices[i]=parent<0?local:mul(matrices[parent],local);
    pos[i]=parent<0?[0,0,0.9]:add(pos[parent],mv(matrices[parent],P.offsets[i]));
  }
  return {positions:pos, rotations:matrices};
}
const project=(p,v)=>[640+240*(v===0?p[0]:v===1?p[1]:(p[0]-p[1])/Math.sqrt(2)),650-300*p[2]];
function observations(u) {
 const p=pose(u), result=[];
 for(let v=0;v<3;v++) for(let i=0;i<8;i++) {
   result.push(...project(p.positions[i],v));
   for(let axis=0;axis<3;axis++) result.push(...project(add(p.positions[i],p.rotations[i].map(row=>row[axis]*0.16)),v));
 }
 return result;
}
module.exports={P,pose,observations};
