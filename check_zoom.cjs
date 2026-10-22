const fs=require("fs");
const r=JSON.parse(fs.readFileSync("index-verify/report.json","utf8"));
const t=r.issues.filter(x=>/data\/tiles/.test(x));
const zs={};
t.forEach(x=>{const m=x.match(/tiles\/[^/]+\/(\d+)\//); if(m) zs[m[1]]=(zs[m[1]]||0)+1;});
console.log(zs);
