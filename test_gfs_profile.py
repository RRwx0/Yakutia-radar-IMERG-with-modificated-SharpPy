from datetime import datetime, timezone

from radar.grid import Grid
from radar.sources.gfs import fetch

r = fetch(Grid(), datetime(2026, 10, 18, 0, 0, tzinfo=timezone.utc))
print("env:", bool(r))
if r:
    print("t2m", r["t2m"].shape, "shear max", float(r["shear"].max()))
    p = r.get("profile")
    print("profile:", None if not p else (p["levels"], p["t"].shape))
