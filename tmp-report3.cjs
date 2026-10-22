const fs=require("fs");
const r=JSON.parse(fs.readFileSync("index-verify/report.json","utf8"));
console.log("status",r.status,"network",r.network,"interactions",r.interactions);
r.issues.filter(x=>/console|overflow|unnamed|heading/.test(x)).forEach(x=>console.log("ISSUE:",x.slice(0,200)));
const tiles=r.issues.filter(x=>/tiles/.test(x));
console.log("tile issues",tiles.length, tiles.slice(0,2));
