const fs=require("fs");
const r=JSON.parse(fs.readFileSync("index-verify/report.json","utf8"));
const local=r.issues.filter(x=>/data\/tiles/.test(x)).slice(0,4);
local.forEach(x=>console.log(x.slice(0,200)));
console.log("total issues", r.issues.length);
