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

print("живой IMERG (HTML):", all(x in idx for x in ["liveToggle", "liveStat", "liveCountdown", "liveNowBtn"]))
print("живой IMERG (JS):", all(x in app for x in ["LIVE_URL", "liveNow", "scheduleLive"]))
print("обновление 30 мин:", "1800000" in app and "через " in app)
print("новые режимы (HTML):", all(x in idx for x in ["capMax", "shearMax", "thunderEst", "trendArea", "trendPeak", "trendVerdict"]))
print("новые режимы (JS):", all(x in app for x in ["renderThunder", "renderTrend"]))

tile = urllib.request.urlopen(base + "tiles/a20250601T12_00/5/27/8.png", timeout=60).read()
print("архивный тайл:", len(tile), "байт")