import json
import urllib.request

url = "http://127.0.0.1:8080/sharppy.html?station=24959&year=2020&time=2020-06-01T12%3A00Z"
with urllib.request.urlopen(url, timeout=30) as r:
    print("page", r.status, len(r.read()))

with urllib.request.urlopen(
    "http://127.0.0.1:8080/api/sounding/profile?station=24959&time=2020-06-01T12%3A00Z",
    timeout=120,
) as r:
    p = json.loads(r.read())
    print("profile", r.status, p["name"], p["time"])
    print("indices", p["indices"]["lcl"], p["indices"]["cape"], p["indices"]["pw"])
