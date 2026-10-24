import re
from pathlib import Path

import esprima

for f, is_html in [("client/app.js", False), ("client/index.html", True), ("client/sharppy.html", True)]:
    src = Path(f).read_text(encoding="utf-8")
    if is_html:
        blocks = re.findall(r"<script(?![^>]*src)[^>]*>(.*?)</script>", src, re.S)
        ok = True
        for b in blocks:
            try:
                esprima.parseScript(b)
            except Exception as e:
                ok = False
                print(f, "script ERR", str(e)[:100])
        print(f, "scripts:", len(blocks), "OK" if ok else "ERR")
    else:
        try:
            esprima.parseScript(src)
            print(f, "syntax OK")
        except Exception as e:
            print(f, "SYNTAX ERR", str(e)[:100])

html = Path("client/index.html").read_text(encoding="utf-8")
js = Path("client/app.js").read_text(encoding="utf-8")
ids = set(re.findall(r'el\("([A-Za-z0-9_]+)"\)', js))
hid = set(re.findall(r'id="([A-Za-z0-9_]+)"', html))
miss = sorted(i for i in ids if i not in hid)
print("missing ids:", miss)
print("new ids present:", all(x in html for x in ["envToggle", "envSelect", "cellsToggle", "cellsPanel", "cellsCount", "cellsList", "accumArea", "accumStorm", "accumPeak"]))