import json
import urllib.request

# METAR через aviationweather.gov API для основных аэропортов Якутии
stations = ["UEEE", "UERP", "UEMA", "UENN", "UEMO", "UELL", "UERR", "UEST", "UEEE", "UESU", "UERL", "UESS"]
api = "https://aviationweather.gov/api/data/metar?ids=" + ",".join(dict.fromkeys(stations)) + "&format=json"

try:
    req = urllib.request.Request(api, headers={"User-Agent": "Mozilla/5.0 yakutia-radar"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read())
    print("METAR count:", len(data))
    for m in data[:12]:
        print(m.get("icaoId"), "|", m.get("obsTime"), "| t:", m.get("temp"), "| wdir:", m.get("wdir"), "| wspd:", m.get("wspd"), "| gust:", m.get("wgust"), "| wx:", m.get("wxString"))
except Exception as e:
    print("ERR", type(e).__name__, str(e)[:200])