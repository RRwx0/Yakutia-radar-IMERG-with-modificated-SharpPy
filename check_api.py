import json
import urllib.request

for p in ["/api/state", "/api/archive?date=2025-07-15&hour=12", "/api/archive/status?key=test"]:
    try:
        r = urllib.request.urlopen("http://127.0.0.1:8080" + p, timeout=30)
        b = r.read()
        ct = r.headers.get("Content-Type", "")
        print(p, "->", r.status, ct[:30], len(b))
        if "json" in ct:
            j = json.loads(b)
            print("   keys:", sorted(j.keys())[:8])
            if p.startswith("/api/archive"):
                print("   status:", j.get("status"))
    except Exception as e:
        print(p, "ERR", str(e)[:100])