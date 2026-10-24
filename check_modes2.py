import re
from pathlib import Path

import esprima

src = Path("client/app.js").read_text(encoding="utf-8")
try:
    esprima.parseScript(src)
    print("app.js syntax OK")
except Exception as e:
    print("SYNTAX ERR", str(e)[:140])

html = Path("client/index.html").read_text(encoding="utf-8")
ids = set(re.findall(r'el\("([A-Za-z0-9_]+)"\)', src))
hid = set(re.findall(r'id="([A-Za-z0-9_]+)"', html))
miss = sorted(i for i in ids if i not in hid)
print("missing ids:", miss)

for i in ["capMax", "shearMax", "thunderEst", "trendArea", "trendPeak", "trendVerdict"]:
    print(i, "in app.js:", i in src, "| in html:", i in html)

print("renderThunder refs:", src.count("renderThunder"))
print("renderTrend refs:", src.count("renderTrend"))