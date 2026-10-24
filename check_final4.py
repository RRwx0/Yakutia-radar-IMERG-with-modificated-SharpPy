import json
import re
from pathlib import Path

import esprima

# 1) синтаксис всех JS
errors = []
for f in ["client/app.js", "client/sharppy.html"]:
    src = Path(f).read_text(encoding="utf-8")
    if f.endswith(".js"):
        try:
            esprima.parseScript(src)
        except Exception as e:
            errors.append((f, str(e)[:120]))
    else:
        for i, b in enumerate(re.findall(r"<script(?![^>]*src)[^>]*>(.*?)</script>", src, re.S)):
            try:
                esprima.parseScript(b)
            except Exception as e:
                errors.append((f + "#" + str(i), str(e)[:120]))
print("JS errors:", errors if errors else "none")

# 2) id сверка
src = Path("client/app.js").read_text(encoding="utf-8")
ids = set(re.findall(r'el\("([A-Za-z0-9_]+)"\)', src))
for f in ["client/index.html", "client/winter.html"]:
    html = Path(f).read_text(encoding="utf-8")
    hid = set(re.findall(r'id="([A-Za-z0-9_]+)"', html))
    miss = sorted(i for i in ids if i not in hid)
    print(f, "missing ids:", miss or "none")

# 3) архив и GIBS
print("gibs-архив в app.js:", "frame.gibs" in src and 'date >= "2020-01-01"' in src)
idx = Path("client/index.html").read_text(encoding="utf-8")
print("index min=2020:", 'min="2020-01-01"' in idx)
win = Path("client/winter.html").read_text(encoding="utf-8")
print("winter min=2020:", 'min="2020-01-01"' in win)
# server
srv = Path("server/app.py").read_text(encoding="utf-8")
print("server 2020:", '"2020-01-01"' in srv)

# 4) SharPy
sh = Path("client/sharppy.html").read_text(encoding="utf-8")
print("sharppy times_index:", "s.times_index" in sh)
snd = Path("client/snd_data.js").read_text(encoding="utf-8")
s = json.loads(re.search(r"window\.RADAR_SND=(\{.*?\});", snd, re.S).group(1))
print("RADAR_SND keys:", sorted(s.keys()))
print("times_index станции:", {wmo: len(v) for wmo, v in s.get("times_index", {}).items()})
print("recent:", len(s.get("recent", [])), "| latest:", len(s.get("latest", {})))