import re
from pathlib import Path

import esprima

errors = []

# JS по всем файлам
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

# id сверка по обеим страницам
src = Path("client/app.js").read_text(encoding="utf-8")
ids = set(re.findall(r'el\("([A-Za-z0-9_]+)"\)', src))
for f in ["client/index.html", "client/winter.html"]:
    html = Path(f).read_text(encoding="utf-8")
    hid = set(re.findall(r'id="([A-Za-z0-9_]+)"', html))
    miss = sorted(i for i in ids if i not in hid)
    print(f, "missing ids:", miss or "none")

# ключевые функции
print("panels:", all(x in src for x in ["drawSndProfile", "showSounding", "cityForPoint"]))
print("snd_data:", all(x in Path("client/index.html").read_text(encoding="utf-8") for x in ["snd_data.js", "probeSounding"])
      and "snd_data.js" in Path("client/winter.html").read_text(encoding="utf-8"))
print("sharppy new format:", "s.recent" in Path("client/sharppy.html").read_text(encoding="utf-8"))