from pathlib import Path

p = Path("client/app.js")
s = p.read_text(encoding="utf-8")
s = s.replace("nm.textContent = modelCache[model].name + \" · \" + (modelCache[model].valid || \"\");",
              "nm.textContent = modelCache[model].name + \" · \" + (modelCache[model].init || modelCache[model].valid || \"\");")
s = s.replace("nm.textContent = j.name + \" · \" + (j.valid || \"\");",
              "nm.textContent = j.name + \" · \" + (j.init || j.valid || \"\");")
p.write_text(s, encoding="utf-8")
print("model time label", "j.init || j.valid" in s, "cache", "modelCache[model].init" in s)