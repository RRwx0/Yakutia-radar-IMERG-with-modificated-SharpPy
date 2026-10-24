import re
import urllib.request

base = "https://rrwx0.github.io/Yakutia-radar-IMERG-with-modificated-SharpPy/"

for p in ["api/sounding/stations", "api/sounding/times?station=24959&year=2024",
          "api/archive?date=2025-07-15&hour=12", "api/state"]:
    try:
        r = urllib.request.urlopen(base + p, timeout=40)
        b = r.read(120)
        print(p, "->", r.status, r.headers.get("Content-Type", ""))
        print("   body:", b[:80])
    except urllib.error.HTTPError as e:
        print(p, "-> HTTP", e.code, e.headers.get("Content-Type", ""))
        print("   body:", e.read()[:80])
    except Exception as e:
        print(p, "-> ERR", str(e)[:80])