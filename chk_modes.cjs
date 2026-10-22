const fs=require("fs");
const r=JSON.parse(fs.readFileSync("_preview-modes-verify/report.json","utf8"));
console.log("status",r.status);
r.issues.filter(x=>/console|overflow|unnamed/.test(x)).forEach(x=>console.log("ISSUE:",x.slice(0,200)));
console.log("total",r.issues.length);
