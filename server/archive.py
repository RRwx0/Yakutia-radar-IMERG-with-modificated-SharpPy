from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from radar.config import FRAME_MINUTES, PROBE, TILES
from radar.grid import Grid
from radar.pipeline import _iso, _stats
from radar.sources import imerg
from radar.tiles import render_all_zooms

ARCHIVE = Path(__file__).resolve().parents[1] / "data" / "archive"
ARCHIVE.mkdir(parents=True, exist_ok=True)

JOBS: dict[str, dict] = {}
_LOCK = threading.Lock()
GRID = Grid()


def parse_key(date: str, hour: int) -> str:
    return f"{date}_{int(hour):02d}"


def _manifest_path(key: str) -> Path:
    return ARCHIVE / f"{key}.json"


def build(date: str, hour: int) -> dict:
    key = parse_key(date, hour)
    start = time.time()
    end = datetime.fromisoformat(date).replace(tzinfo=timezone.utc) + timedelta(hours=int(hour))
    times = [end - timedelta(minutes=FRAME_MINUTES * (11 - i)) for i in range(12)]

    fields = [imerg.fetch_field(GRID, t) for t in times]
    echo = float(np.mean([100.0 * np.isfinite(f).mean() for f in fields]))

    focus = None
    last = fields[-1]
    wet = np.isfinite(last) & (last >= 30.0)
    if wet.any():
        iy, ix = np.where(wet)
        lat_c = float(GRID.lats[int(np.median(iy))])
        lon_c = float(GRID.lons[int(np.median(ix))])
        focus = [
            [round(max(GRID.lat_min, lat_c - 4.0), 2), round(max(GRID.lon_min, lon_c - 7.0), 2)],
            [round(min(GRID.lat_max, lat_c + 4.0), 2), round(min(GRID.lon_max, lon_c + 7.0), 2)],
        ]

    probe_grid = Grid(step=0.1)
    frames = []
    for i, (when, field) in enumerate(zip(times, fields)):
        fid = f"a{date.replace('-', '')}T{int(hour):02d}_{i:02d}"
        render_all_zooms(GRID, field, TILES / fid)
        probe = probe_grid.sample(field, probe_grid.lat2d, probe_grid.lon2d)
        np.save(PROBE / f"{fid}.npy", np.nan_to_num(probe, nan=-99.0).astype(np.float16))
        stats = _stats(field)
        frames.append(
            {
                "id": fid,
                "kind": "obs",
                "time": _iso(when),
                "lead_min": 0,
                "tile_url": f"/tiles/{fid}/{{z}}/{{x}}/{{y}}.png",
                "stats": stats,
            }
        )

    manifest = {
        "generated_at": _iso(datetime.now(timezone.utc)),
        "generation_seconds": round(time.time() - start, 1),
        "archive": {"date": date, "hour": int(hour), "key": key},
        "region": {
            "name": "Республика Саха (Якутия)",
            "bounds": [[54.0, 104.0], [74.0, 166.0]],
            "grid_step_deg": GRID.step,
            "size": [GRID.ny, GRID.nx],
        },
        "focus": focus,
        "stations": [],
        "coverage_pct": 100.0,
        "echo_coverage_pct": round(echo, 2),
        "nowcast": {"method": "archive", "members": 0, "steps": 0, "step_min": FRAME_MINUTES, "skill": {}},
        "frames": frames,
        "probe": {"step": 0.1},
        "source": imerg.describe(),
    }
    _manifest_path(key).write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return manifest


def status(job: str) -> dict:
    with _LOCK:
        return dict(JOBS.get(job, {"status": "unknown"}))


def request(date: str, hour: int) -> dict:
    key = parse_key(date, hour)
    if _manifest_path(key).exists():
        return {"status": "done", "key": key, "manifest": json.loads(_manifest_path(key).read_text(encoding="utf-8"))}

    with _LOCK:
        job = JOBS.get(key)
        if job and job.get("status") == "building":
            return {"status": "building", "key": key}
        JOBS[key] = {"status": "building", "started": time.time()}

    def worker():
        try:
            manifest = build(date, hour)
            with _LOCK:
                JOBS[key] = {"status": "done", "manifest": manifest}
        except Exception as exc:  # noqa: BLE001
            with _LOCK:
                JOBS[key] = {"status": "error", "error": str(exc)}

    threading.Thread(target=worker, daemon=True).start()
    return {"status": "building", "key": key}
