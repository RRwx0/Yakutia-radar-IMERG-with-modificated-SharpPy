import json
import urllib.request

with urllib.request.urlopen("http://127.0.0.1:8080/api/model_field?model=gfs", timeout=240) as r:
    j = json.loads(r.read())
print("keys", sorted(j.keys()))
print("init", j.get("init"), "valid", j.get("valid"), "note", j.get("note"))
print("model", j.get("model"), "max_dbz", j.get("max_dbz"))