// Broken baseline: assumes that controls are independent and ignores coupling.
const fs=require('node:fs'), client=require('./client.cjs');
async function fit(k,target) {let u=Array(24).fill(0);await client.query(k,u);return u;}
async function main() {const targets=await client.targets();fs.mkdirSync('/app/out',{recursive:true});for(const k of ['a','b','c']) fs.writeFileSync(`/app/out/controls_case_${k}.json`,JSON.stringify(await fit(k,targets[k])));}
if(require.main===module)main().catch(e=>{console.error(e);process.exit(1);});
module.exports={fit};
