import re
from pathlib import Path

# 1) sharppy.html использует snd_data.js
sh = Path("client/sharppy.html").read_text(encoding="utf-8")
print("sharppy loads:", "snd_data.js" in sh, "| uses recent:", "s.recent" in sh,
      "| uses latest:", "s.latest" in sh or "latest" in sh)

# 2) обе страницы подключают snd_data.js
for f in ["client/index.html", "client/winter.html"]:
    html = Path(f).read_text(encoding="utf-8")
    print(f, "snd_data.js:", "snd_data.js" in html, "| data:", "data.js" in html or "winter_data.js" in html)

# 3) проверка структуры RADAR_SND
snd = Path("client/snd_data.js").read_text(encoding="utf-8")
import json
m = re.search(r"window\.RADAR_SND=(\{.*?\});", snd, re.S)
s = json.loads(m.group(1))
print("RADAR_SND keys:", sorted(s.keys()))
print("  latest станций:", {wmo: s["latest"][wmo]["name"] for wmo in list(s["latest"].keys())[:4]})
print("  recent:", len(s["recent"]), "| first:", s["recent"][0]["wmo"], s["recent"][0]["time"] if s["recent"] else "-")
# профиль recent содержит level? (для sharppy drawSkew нужно p.levels)
print("  recent[0].profile keys:", sorted(s["recent"][0]["profile"].keys()) if s["recent"] else "-")