import re
from pathlib import Path

import esprima

src = Path("client/app.js").read_text(encoding="utf-8")
try:
    esprima.parseScript(src)
    print("app.js syntax OK")
except Exception as e:
    print("SYNTAX ERR", str(e)[:140])

for f in ["client/index.html", "client/winter.html"]:
    html = Path(f).read_text(encoding="utf-8")
    ids = set(re.findall(r'el\("([A-Za-z0-9_]+)"\)', src))
    hid = set(re.findall(r'id="([A-Za-z0-9_]+)"', html))
    miss = sorted(i for i in ids if i not in hid)
    print(f, "missing ids:", miss)
    print(f, "winter flag:", "class=\"winter\"" in html)

css = Path("client/styles.css").read_text(encoding="utf-8")
print("winter css:", "body.winter" in css)
print("IS_WINTER in app.js:", "IS_WINTER" in src)