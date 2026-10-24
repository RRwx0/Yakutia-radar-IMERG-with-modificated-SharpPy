import re
from pathlib import Path

import esprima

src = Path("client/app.js").read_text(encoding="utf-8")
try:
    esprima.parseScript(src)
    print("app.js OK")
except Exception as e:
    print("app.js ERR", str(e)[:120])

for f in ["client/index.html", "client/winter.html"]:
    html = Path(f).read_text(encoding="utf-8")
    ids = set(re.findall(r'el\("([A-Za-z0-9_]+)"\)', src))
    hid = set(re.findall(r'id="([A-Za-z0-9_]+)"', html))
    miss = sorted(i for i in ids if i not in hid)
    print(f, "missing ids:", miss)

idx = Path("client/index.html").read_text(encoding="utf-8")
win = Path("client/winter.html").read_text(encoding="utf-8")
print("index -> winter link:", 'href="winter.html"' in idx)
print("winter -> index link:", 'href="index.html"' in win)
print("winter flag on body:", 'class="winter"' in win)
print("winter branding:", "ЗИМНИЙ РАДАР" in win and "ноябрь–март" in win)
print("winter css:", "body.winter" in Path("client/styles.css").read_text(encoding="utf-8"))