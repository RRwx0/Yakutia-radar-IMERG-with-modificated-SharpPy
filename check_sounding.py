import json
import urllib.request

for p in [
    "/api/sounding/stations",
    "/api/sounding/times?station=24959&year=2024",
    "/api/sounding/profile?station=24959&time=2024-07-15T12:00:00Z",
]:
    try:
        r = urllib.request.urlopen("http://127.0.0.1:8080" + p, timeout=60)
        b = r.read()
        ct = r.headers.get("Content-Type", "")
        print(p, "->", r.status, ct[:30], len(b))
        if "json" in ct and len(b) < 2000:
            print("   ", json.loads(b))
    except Exception as e:
        print(p, "ERR", str(e)[:120])