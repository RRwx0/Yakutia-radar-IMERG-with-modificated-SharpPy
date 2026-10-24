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
win = get("winter.html")
sh = get("sharppy.html")
app = get("app.js")
snd = get("snd_data.js")

print("index:", "snd_data.js" in idx, "| probeSounding:", "probeSounding" in idx)
print("winter:", "snd_data.js" in win, "| probeSounding:", "probeSounding" in win)
print("sharppy: recent-формат:", "s.recent" in sh)
print("app.js: drawSndProfile:", "drawSndProfile" in app, "| cityForPoint:", "cityForPoint" in app)

m = re.search(r"window\.RADAR_SND=(\{.*?\});", snd, re.S)
s = json.loads(m.group(1)) if m else {}
print("RADAR_SND keys:", sorted(s.keys()))
print("latest:", {wmo: s["latest"][wmo]["name"] for wmo in list(s["latest"].keys())[:6]})
print("recent:", len(s.get("recent", [])), "профилей")
print("city_stations:", len(s.get("city_stations", {})), "городов")

# новый стиль в css
css = get("styles.css")
print("css новый фон:", "1200px 700px" in css, "| шапка акцент:", "inset 0 2px 0" in css)