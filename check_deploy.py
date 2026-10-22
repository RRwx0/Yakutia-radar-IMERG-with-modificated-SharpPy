import urllib.request
from pathlib import Path

import server.app as mod

print("cors in code", any("CORSMiddleware" in str(m) for m in mod.app.user_middleware))

for path in ["/", "/sharppy.html", "/config.js"]:
    with urllib.request.urlopen("http://127.0.0.1:8080" + path, timeout=15) as r:
        print(path, r.status, len(r.read()))

req = urllib.request.Request(
    "http://127.0.0.1:8080/api/sounding/stations",
    headers={"Origin": "https://example.github.io"},
)
with urllib.request.urlopen(req, timeout=30) as r:
    print("acao", r.headers.get("Access-Control-Allow-Origin"))

s = Path("client/app.js").read_text(encoding="utf-8")
print("API refs", s.count('API + "/api/'), "config in html", 'config.js' in Path("client/index.html").read_text(encoding="utf-8"))
