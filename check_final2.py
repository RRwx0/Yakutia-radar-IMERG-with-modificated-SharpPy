import re
from pathlib import Path

import esprima

# JS синтаксис всех страниц
try:
    esprima.parseScript(Path("client/app.js").read_text(encoding="utf-8"))
    print("app.js OK")
except Exception as e:
    print("app.js ERR", str(e)[:120])

for f in ["client/index.html", "client/winter.html", "client/sharppy.html"]:
    src = Path(f).read_text(encoding="utf-8")
    blocks = re.findall(r"<script(?![^>]*src)[^>]*>(.*?)</script>", src, re.S)
    ok = True
    for b in blocks:
        try:
            esprima.parseScript(b)
        except Exception as e:
            ok = False
            print(f, "script ERR", str(e)[:100])
    print(f, "scripts OK" if ok else "ERR", len(blocks))

# id сверка для обеих страниц main
src = Path("client/app.js").read_text(encoding="utf-8")
ids = set(re.findall(r'el\("([A-Za-z0-9_]+)"\)', src))
for f in ["client/index.html", "client/winter.html"]:
    html = Path(f).read_text(encoding="utf-8")
    hid = set(re.findall(r'id="([A-Za-z0-9_]+)"', html))
    miss = sorted(i for i in ids if i not in hid)
    print(f, "missing ids:", miss)

# ключевые фичи
win = Path("client/winter.html").read_text(encoding="utf-8")
print("snowOnly:", "snowOnlyToggle" in win, "| fullscreen:", "fullscreenBtn" in win,
      "| weather:", "weatherToggle" in win, "| winter_data:", "winter_data.js" in win)
print("IS_WINTER:", "IS_WINTER" in src, "| renderSnow:", "renderSnow" in src,
      "| loadWind:", "loadWind" in src, "| toggleFullscreen:", "toggleFullscreen" in src)