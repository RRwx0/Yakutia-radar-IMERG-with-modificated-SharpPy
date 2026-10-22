const fs=require("fs");
const r=JSON.parse(fs.readFileSync("index-verify/report.json","utf8"));
console.log("status",r.status,"total",r.issues.length);
r.issues.filter(x=>/console|overflow|unnamed/.test(x)).forEach(x=>console.log("ISSUE:",x.slice(0,200)));
