const fs=require("fs");
const r=JSON.parse(fs.readFileSync("client/index-verify/report.json","utf8"));
const t=r.issues.filter(x=>/tiles/.test(x));
console.log("tile issues", t.length, t.slice(0,2));
