import json
import re
import urllib.request

base = "https://rrwx0.github.io/Yakutia-radar-IMERG-with-modificated-SharpPy/"


def get(p, binary=False):
    try:
        b = urllib.request.urlopen(base + p, timeout=60).read()
        return b if binary else b.decode("utf-8", "replace")
    except Exception as e:
        return ("ERR " + str(e)).encode() if binary else "ERR " + str(e)


win = get("winter.html")
app = get("app.js")
wdata = get("winter_data.js")

print("winter.html:", len(win), "| ЗИМНИЙ РАДАР:", "ЗИМНИЙ РАДАР" in win)
print("snowOnlyToggle:", "snowOnlyToggle" in win, "| weatherToggle:", "weatherToggle" in win,
      "| fullscreenBtn:", "fullscreenBtn" in win)
print("winter_data.js:", len(wdata), "| RADAR_STATE:", "window.RADAR_STATE" in wdata)
print("app.js: renderSnow:", "renderSnow" in app, "| loadWind:", "loadWind" in app,
      "| toggleFullscreen:", "toggleFullscreen" in app, "| IS_WINTER:", "IS_WINTER" in app)

m = re.search(r"window\.RADAR_STATE=(\{.*?\});", wdata, re.S)
st = json.loads(m.group(1)) if m else {}
frames = st.get("manifest", {}).get("frames", [])
print("зимних кадров:", len(frames), "| первый:", frames[0]["id"] if frames else "-")

tile = get("tiles/w20251225T12_06/5/27/8.png", binary=True)
print("зимний тайл:", (tile[:4] if tile.startswith(b"\x89PNG") else tile[:40]), len(tile) if isinstance(tile, bytes) else 0)