import json
from pathlib import Path

import numpy as np

from radar.grid import Grid
from radar.sources import models

root = Path("client")
data_js = root / "data.js"
data_dir = Path("data")

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

# --- архивные кадры: манифесты, для которых тайлы уже лежат в client/tiles ---
tiles_dir = root / "tiles"
arch_dates = []
for mf in sorted((data_dir / "archive").glob("*.json")):
    try:
        manifest = json.loads(mf.read_text(encoding="utf-8"))
    except Exception:
        continue
    frames = manifest.get("frames", [])
    have = all((tiles_dir / f["id"]).is_dir() for f in frames)
    key = manifest.get("archive", {}).get("key") or mf.stem
    if have:
        arch_dates.append({
            "key": key,
            "date": manifest.get("archive", {}).get("date"),
            "hour": manifest.get("archive", {}).get("hour"),
            "frames": frames,
            "source": manifest.get("source"),
            "focus": manifest.get("focus"),
            "echo_coverage_pct": manifest.get("echo_coverage_pct"),
        })
        print("archive ok", key, len(frames))
    else:
        print("archive skip (no tiles)", key)
static["archive"] = {"dates": arch_dates}

# --- данные зондирований IGRA: станции + индекс сроков + несколько профилей ---
snd_data = {"stations": [], "times": {}, "profiles": []}
try:
    from server import sounding as snd

    stations_list = [{"wmo": k, "name": v[0], "lat": v[1], "lon": v[2]} for k, v in snd.STATIONS.items()]
    snd_data["stations"] = stations_list
    # индекс сроков для текущего года и прошлого — по всем станциям, у которых есть архив
    from pathlib import Path as P

    for wmo in snd.STATIONS:
        zpath = snd._zip_path(wmo)
        if not zpath.exists() or zpath.stat().st_size < 1_000_000:
            continue
        try:
            t = snd.times(wmo, None)
            snd_data["times"][wmo] = t
            print("sounding index", wmo, len(t))
        except Exception as e:
            print("sounding index err", wmo, type(e).__name__, e)
    # пара показательных профилей (Якутск: лето и зима)
    for wmo, iso in [("24959", "2025-07-15T12:00Z"), ("24959", "2025-01-15T00:00Z")]:
        try:
            p = snd.profile(wmo, iso)
            if p:
                snd_data["profiles"].append(p)
                print("profile ok", wmo, iso, len(p.get("levels", [])))
        except Exception as e:
            print("profile err", wmo, iso, type(e).__name__, e)
except Exception as e:
    print("snd_data err", type(e).__name__, e)

# --- запись: данные в data.js, зондирования в отдельный snd_data.js ---
existing = data_js.read_text(encoding="utf-8")
if not existing.endswith("\n"):
    existing += "\n"
chunk = "\nwindow.RADAR_STATIC=" + json.dumps(static, ensure_ascii=False) + ";\n"
if "window.RADAR_STATIC=" in existing:
    k = existing.find("window.RADAR_STATIC=")
    existing = existing[:k].rstrip() + "\n"
data_js.write_text(existing + chunk, encoding="utf-8")
print("data.js", data_js.stat().st_size)

snd_js = root / "snd_data.js"
snd_js.write_text(
    "\nwindow.RADAR_SND=" + json.dumps(snd_data, ensure_ascii=False) + ";\n",
    encoding="utf-8",
)
print("snd_data.js", snd_js.stat().st_size)