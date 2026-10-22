import urllib.request

def get(path):
    with urllib.request.urlopen("http://127.0.0.1:8080" + path, timeout=120) as r:
        return r.status, r.read()

st, body = get("/api/models")
print("models", st, body.decode("utf-8", "replace")[:300])

st, body = get("/api/model_field?model=gfs")
import json
try:
    j = json.loads(body)
    print("field", st, j.get("model"), j.get("valid"), j.get("max_dbz"), "nonull", sum(1 for x in j.get("field", []) if x is not None))
except Exception as e:
    print("field parse err", e, body[:200])

for p in ["/", "/sharppy.html"]:
    st, body = get(p)
    print("page", p, st, len(body))