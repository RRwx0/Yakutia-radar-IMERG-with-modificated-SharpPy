const fs=require("fs");
const r=JSON.parse(fs.readFileSync("index-verify/report.json","utf8"));
console.log("status",r.status,"network",r.network,"interactions",r.interactions);
r.issues.filter(x=>!/broken image|blocked resource/.test(x)).forEach(x=>console.log("ISSUE:",x.slice(0,240)));
const local=r.issues.filter(x=>/data\/tiles/.test(x));
console.log("local tile issues:",local.length);
