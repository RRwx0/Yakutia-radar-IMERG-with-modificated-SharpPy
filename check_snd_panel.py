import re
from pathlib import Path

import esprima

src = Path("client/app.js").read_text(encoding="utf-8")
try:
    esprima.parseScript(src)
    print("app.js syntax OK")
except Exception as e:
    print("SYNTAX ERR", str(e)[:160])

ids = set(re.findall(r'el\("([A-Za-z0-9_]+)"\)', src))
mis = []
for f in ["client/index.html", "client/winter.html"]:
    html = Path(f).read_text(encoding="utf-8")
    hid = set(re.findall(r'id="([A-Za-z0-9_]+)"', html))
    miss = sorted(i for i in ids if i not in hid)
    print(f, "missing ids:", miss)

new_ids = ["probeSounding", "sndSkew", "sndMeta", "sndCape", "sndLi", "sndPw", "sndShear", "sndSrh"]
for i in new_ids:
    print(i, "| in app.js:", i in src, "| in index.html:", i in Path("client/index.html").read_text(encoding="utf-8"))

print("showSounding refs:", src.count("showSounding"))
print("drawSndProfile refs:", src.count("drawSndProfile"))
print("cityForPoint refs:", src.count("cityForPoint"))
print("mk.on click:", src.count('mk.on("click"'))