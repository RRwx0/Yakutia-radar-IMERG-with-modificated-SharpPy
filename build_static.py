import json
from pathlib import Path

import numpy as np

from radar.grid import Grid
from radar.sources import models

root = Path("client")
data_js = root / "data.js"

static = {}

try:
    m = models.fetch(Grid(), "gfs")
    if m and "field" in m:
        field = m["field"]
        coarse = Grid(step=1.0)
        ny, nx = coarse.ny, coarse.nx
        arr = np.full(ny * nx, None, dtype=object)
        for iy in range(ny):
            lat = coarse.lat_min + iy * coarse.step
            fi = int(round((lat - 54.0) / 0.03))
            fi = max(0, min(field.shape[0] - 1, fi))
            row = field[fi, :]
            for ix in range(nx):
                lon = coarse.lon_min + ix * coarse.step
                fj = int(round((lon - 104.0) / 0.03))
                fj = max(0, min(field.shape[1] - 1, fj))
                v = row[fj]
                arr[iy * nx + ix] = None if not np.isfinite(v) else round(float(v), 1)
        static["model"] = {
            "model": "gfs",
            "name": m.get("name", "GFS (NOAA)"),
            "valid": m.get("valid"),
            "step": 1.0,
            "lat0": coarse.lat_min,
            "lon0": coarse.lon_min,
            "ny": ny,
            "nx": nx,
            "field": arr.tolist(),
        }
        print("model ok", ny, "x", nx)
    else:
        print("model unavailable")
except Exception as e:
    print("model err", type(e).__name__, e)

# дописываем в data.js отдельной глобальной переменной
existing = data_js.read_text(encoding="utf-8")
if not existing.endswith("\n"):
    existing += "\n"
chunk = "\nwindow.RADAR_STATIC=" + json.dumps(static, ensure_ascii=False) + ";\n"
# убираем старый RADAR_STATIC, если был
if "window.RADAR_STATIC=" in existing:
    k = existing.find("window.RADAR_STATIC=")
    existing = existing[:k].rstrip() + "\n"
data_js.write_text(existing + chunk, encoding="utf-8")
print("data.js", data_js.stat().st_size)