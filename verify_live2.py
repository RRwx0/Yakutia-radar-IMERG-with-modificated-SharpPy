import json
import re
import urllib.request

base = "https://rrwx0.github.io/Yakutia-radar-IMERG-with-modificated-SharpPy/"


def get(p):
    try:
        return urllib.request.urlopen(base + p, timeout=60).read().decode("utf-8", "replace")
    except Exception as e:
        return "ERR " + str(e)


idx = get("index.html")
app = get("app.js")
data = get("data.js")

print("официальный стиль:", "ЯКУТГИДРОМЕТ" in idx)
print("старый бренд убран:", "IMERG · САХА" in idx or "IMERG · Саха —" in idx)
print("новые режимы (HTML):", all(x in idx for x in ["envToggle", "cellsToggle", "accumArea"]))
print("новые режимы (JS):", all(x in app for x in ["drawEnv", "renderCellsPanel", "renderAccum"]))
print("наукастинг убран:", "Наукастинг" not in idx)

m = re.search(r"window\.RADAR_STATIC=(\{.*?\});\s*$", data, re.S)
st = json.loads(m.group(1)) if m else {}
dates = [d["key"] for d in st.get("archive", {}).get("dates", [])]
print("архив в статике (даты):", len(dates))
for d in dates:
    print("  ", d)

# проверим тайл нового архивного дня
tile = urllib.request.urlopen(base + "tiles/a20260618T12_11/5/27/8.png", timeout=60).read()
print("тайл нового архивного дня:", len(tile), "байт,", tile[:4])