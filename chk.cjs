const fs=require("fs");
const r=JSON.parse(fs.readFileSync("index-verify/report.json","utf8"));
console.log("status",r.status,"interactions",r.interactions);
r.issues.filter(x=>/console|overflow|unnamed|heading/.test(x)).forEach(x=>console.log("ISSUE:",x.slice(0,240)));
console.log("total", r.issues.length);
