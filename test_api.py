from fastapi.testclient import TestClient
from server.app import app
c = TestClient(app)
print("health", c.get("/api/health").status_code)
r = c.get("/api/archive?date=2025-06-01&hour=12")
print("archive", r.status_code, list(r.json().keys())[:4], r.json().get("status"))
r2 = c.get("/api/archive/status?key=2025-06-01_12")
body = r2.json()
print("status", body.get("status"), "frames", len(body.get("manifest", {}).get("frames", [])))
r3 = c.get("/api/accum?lat=64&lon=140&frame=obs_11&window=6")
print("accum", r3.status_code, r3.json())
