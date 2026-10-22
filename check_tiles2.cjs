const fs=require("fs");
const r=JSON.parse(fs.readFileSync("index-verify/report.json","utf8"));
const t=r.issues.filter(x=>/tiles/.test(x));
console.log("tile issues", t.length);
const zs={};
t.forEach(x=>{const m=x.match(/tiles\/[^/]+\/(\d+)\//); if(m) zs[m[1]]=(zs[m[1]]||0)+1;});
console.log(zs);
console.log(t.slice(0,3));
