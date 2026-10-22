import pathlib
p = pathlib.Path("client/app.js")
s = p.read_text(encoding="utf-8")
s = s.replace('  map.createPane("zones").style.zIndex = 360;\n', "")
p.write_text(s, encoding="utf-8")
print("zones refs:", s.count("zones"))
