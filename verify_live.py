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
print("him UI:", "himToggle" in idx and "himCountdown" in idx)
print("him JS :", "HIM_LAYER" in app and "himNow" in app)
print("warn UI gone:", "warnToggle" not in idx and "warnPanel" not in idx)
print("warn JS gone:", "loadWarnings" not in app and "warnLayer" not in app)
m = re.search(r"window\.RADAR_STATIC=(\{.*?\});\s*$", data, re.S)
print("static keys:", sorted(re.findall(r'"(\w+)":', m.group(1))) if m else "none")