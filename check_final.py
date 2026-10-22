import json
import urllib.parse
import urllib.request

base = "http://127.0.0.1:8080"
t = urllib.parse.quote("2020-06-01T12:00Z")
with urllib.request.urlopen(f"{base}/api/sounding/profile?station=24959&time={t}", timeout=120) as r:
    p = json.loads(r.read())
print("indices", p["indices"])
print("td levels", sum(1 for x in p["levels"] if x["td"] is not None))
with urllib.request.urlopen(base + "/sharppy.html", timeout=30) as r:
    print("page", r.status, len(r.read()))
