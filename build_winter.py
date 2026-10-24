import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from radar.config import FRAME_MINUTES
from radar.grid import Grid
from radar.pipeline import _iso, _stats
from radar.sources import imerg
from radar.tiles import render_all_zooms

ROOT = Path("client")
TILES = ROOT / "tiles"
GRID = Grid()
COARSE = Grid(step=1.0)

WINTER_DAY = "2025-12-25"
HOUR = 12


def fetch_retry(grid, when, tries=3):
    last = None
    for i in range(tries):
        try:
            f = imerg.fetch_field(grid, when)
            if np.isfinite(f).sum() > 0:
                return f
            last = f
            time.sleep(1.5)
        except Exception as e:
            last = None
            time.sleep(2)
    return last


def build():
    start = time.time()
    end = datetime.fromisoformat(WINTER_DAY).replace(tzinfo=timezone.utc) + timedelta(hours=HOUR)
    times = [end - timedelta(minutes=FRAME_MINUTES * (11 - i)) for i in range(12)]

    frames = []
    probe_frames = {}
    probe_phase = {}
    total_cov = 0.0
    for i, when in enumerate(times):
        fid = f"w{WINTER_DAY.replace('-', '')}T{HOUR:02d}_{i:02d}"
        field = fetch_retry(GRID, when)
        if field is None:
            print("SKIP (no data)", fid)
            continue
        if not (TILES / fid).exists():
            render_all_zooms(GRID, field, TILES / fid)
        print("ok", fid, "finite:", int(np.isfinite(field).sum()))

        vals = COARSE.sample(field, COARSE.lat2d, COARSE.lon2d)
        arr = [None if (not np.isfinite(v) or v < 5) else round(float(v), 1) for v in vals.ravel()]
        probe_frames[fid] = arr
        phase = np.where(np.isfinite(vals) & (vals >= 5), 1, 0).astype(np.int8)
        probe_phase[fid] = phase.tolist()
        total_cov += float(np.isfinite(field).sum()) / GRID.lat2d.size

        stats = _stats(field)
        frames.append({
            "id": fid, "kind": "obs", "time": _iso(when), "lead_min": 0,
            "tile_url": f"/tiles/{fid}/{{z}}/{{x}}/{{y}}.png", "stats": stats,
        })
        time.sleep(0.5)

    if not frames:
        print("NO FRAMES BUILT")
        return
    avg_cov = 100.0 * total_cov / len(frames)
    manifest = {
        "generated_at": _iso(datetime.now(timezone.utc)),
        "generation_seconds": round(time.time() - start, 1),
        "region": {"name": "Республика Саха (Якутия)", "bounds": [[54.0, 104.0], [74.0, 166.0]],
                   "grid_step_deg": GRID.step, "size": [GRID.ny, GRID.nx]},
        "focus": None,
        "stations": [],
        "coverage_pct": 100.0,
        "echo_coverage_pct": round(avg_cov, 2),
        "nowcast": {"method": "persistence", "members": 0, "steps": 0, "step_min": FRAME_MINUTES, "skill": {}},
        "frames": frames,
        "probe": {"step": COARSE.step},
        "phase": {
            "snow_pct": 100.0, "mixed_pct": 0.0, "rain_pct": 0.0,
            "wetbulb_min": None, "wetbulb_max": None,
            "note": "зимний набор: осадки классифицированы как снег"
        },
        "source": imerg.describe(),
    }

    data_js = ROOT / "data.js"
    import re
    text = data_js.read_text(encoding="utf-8")
    m = re.search(r"window\.RADAR_STATE=(\{.*?\});", text, re.S)
    state = json.loads(m.group(1))
    out = {
        "manifest": manifest,
        "env": state.get("env"),
        "probe": {
            "frames": probe_frames,
            "phase": probe_phase,
            "lat0": COARSE.lat_min,
            "lon0": COARSE.lon_min,
            "step": COARSE.step,
            "nx": COARSE.nx,
            "ny": COARSE.ny,
        },
    }

    # встроенный архив для зимней страницы: сам зимний день
    static = {
        "archive": {
            "dates": [{
                "key": f"{WINTER_DAY}_{HOUR:02d}",
                "date": WINTER_DAY,
                "hour": HOUR,
                "frames": frames,
                "source": imerg.describe(),
                "focus": None,
                "echo_coverage_pct": manifest["echo_coverage_pct"],
            }]
        }
    }

    winter_js = ROOT / "winter_data.js"
    winter_js.write_text(
        "\nwindow.RADAR_STATE=" + json.dumps(out, ensure_ascii=False) + ";\n" +
        "\nwindow.RADAR_STATIC=" + json.dumps(static, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    print("winter_data.js", winter_js.stat().st_size, "bytes | frames:", len(frames), "| avg cov:", round(avg_cov, 2), "%")
    # освобождаем старые пустые тайлы
    import shutil
    old = "w20250115T12"
    for p in TILES.iterdir():
        if p.is_dir() and p.name.startswith(old) and p.name not in [f["id"] for f in frames]:
            shutil.rmtree(p, ignore_errors=True)
            print("removed empty tiles", p.name)


if __name__ == "__main__":
    build()