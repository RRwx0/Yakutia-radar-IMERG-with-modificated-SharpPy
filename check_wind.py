import re
from pathlib import Path

import esprima

src = Path("client/app.js").read_text(encoding="utf-8")
try:
    esprima.parseScript(src)
    print("app.js syntax OK")
except Exception as e:
    print("SYNTAX ERR", str(e)[:140])

html = Path("client/winter.html").read_text(encoding="utf-8")
ids = set(re.findall(r'el\("([A-Za-z0-9_]+)"\)', src))
hid = set(re.findall(r'id="([A-Za-z0-9_]+)"', html))
miss = sorted(i for i in ids if i not in hid)
print("winter.html missing ids:", miss)

for i in ["weatherToggle", "weatherPanel", "weatherList", "weatherUpdated"]:
    print(i, "in app.js:", i in src, "| in winter.html:", i in html)

print("wind code refs:", src.count("loadWind"), src.count("windArrowHtml"), src.count("WIND_CITIES"))
print("winter_data.js in winter.html:", "winter_data.js" in html)