from __future__ import annotations

import json
import math
import shutil
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np

from .config import (
    CLIENT,
    DBZ_FLOOR,
    FRAME_MINUTES,
    NOWCAST_STEPS,
    OBS_FRAMES,
    DATA,
    PROBE,
    STATIONS,
    TILES,
    VOLUMES,
    frame_times,
)
from .grid import Grid
from .mosaic import build_mosaic
from .nowcast import advect, estimate_flow, forecast, skill
from .qc import clean_ppi
from .sources import gfs, imerg
from . import phase as phase_mod
from . import severe
from .cells import cell_growth, detect_cells
from .classify import TYPE_META
from .sources.netcdf_source import read_volume
from .tiles import render_all_zooms

CELL_KM2 = 5.3
PROBE_STEP = 0.1


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _stats(field: np.ndarray) -> dict:
    if not np.isfinite(field).any():
        return {"max_dbz": None, "area_30_km2": 0, "echo_pct": 0.0}
    valid = np.isfinite(field)
    area = float((field > 30).sum() * CELL_KM2)
    return {
        "max_dbz": round(float(np.nanmax(field)), 1),
        "area_30_km2": int(area),
        "echo_pct": round(100.0 * (valid & (field >= DBZ_FLOOR)).sum() / field.size, 2),
    }


def _clean(obj):
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, np.floating):
        value = float(obj)
        return value if math.isfinite(value) else None
    if isinstance(obj, np.integer):
        return int(obj)
    return obj


def run(regenerate: bool = True) -> dict:
    started = time.time()
    grid = Grid()
    times = imerg.frames(OBS_FRAMES)
    mosaics = [imerg.fetch_field(grid, t) for t in times]
    echo_pct = float(np.mean([100.0 * np.isfinite(m).mean() for m in mosaics]))
    visibility_pct = 100.0

    env = gfs.fetch(grid, times[-1])
    phase_code = wet = None
    if env is not None:
        phase_code, wet = phase_mod.classify(env["t2m"], env["rh2m"])
        np.savez_compressed(
            DATA / "env.npz",
            t2m=env["t2m"].astype(np.float32),
            rh2m=env["rh2m"].astype(np.float32),
            cape=env["cape"].astype(np.float32),
            shear=env["shear"].astype(np.float32),
            phase=phase_code.astype(np.int8),
            wetbulb=wet.astype(np.float32),
        )

    method = "advection"
    last_skill = {}
    if len(mosaics) > 1:
        u_s, v_s = estimate_flow(mosaics[-2], mosaics[-1])
        last_skill = skill(mosaics[-2], advect(mosaics[-2], u_s, v_s), mosaics[-1])
        adv_mae = last_skill.get("advection_mae", 1e9)
        per_mae = last_skill.get("persistence_mae", 1e9)
        if adv_mae >= 0.98 * per_mae:
            method = "persistence"

    result = forecast(mosaics, steps=NOWCAST_STEPS, members=5, method=method)

    if TILES.exists():
        shutil.rmtree(TILES)
    TILES.mkdir(parents=True, exist_ok=True)
    PROBE.mkdir(parents=True, exist_ok=True)
    for old in PROBE.glob("*.npy"):
        old.unlink()

    probe_grid = Grid(step=PROBE_STEP)
    frames = []

    for i, (when, field) in enumerate(zip(times, mosaics)):
        if phase_code is not None:
            field = phase_mod.adjust_dbz(field, phase_code, wet)
        frames.append(
            {
                "id": f"obs_{i:02d}",
                "kind": "obs",
                "time": _iso(when),
                "lead_min": 0,
                "field": field,
                "prob": None,
            }
        )

    base_time = times[-1]
    for k in range(NOWCAST_STEPS):
        when = base_time + timedelta(minutes=FRAME_MINUTES * (k + 1))
        field = result["frames"][k]
        if phase_code is not None:
            field = phase_mod.adjust_dbz(field, phase_code, wet)
        frames.append(
            {
                "id": f"fc_{k:02d}",
                "kind": "nowcast",
                "time": _iso(when),
                "lead_min": FRAME_MINUTES * (k + 1),
                "field": field,
                "prob": result["prob30"][k],
            }
        )

    manifest_frames = []
    prev_cells: list[dict] | None = None
    for frame in frames:
        root = TILES / frame["id"]
        zoom_info = render_all_zooms(grid, frame["field"], root)

        probe = probe_grid.sample(frame["field"], probe_grid.lat2d, probe_grid.lon2d)
        np.save(PROBE / f"{frame['id']}.npy", np.nan_to_num(probe, nan=-99.0).astype(np.float16))

        if frame["prob"] is not None:
            prob_probe = probe_grid.sample(frame["prob"], probe_grid.lat2d, probe_grid.lon2d)
            np.save(PROBE / f"{frame['id']}_prob.npy", np.nan_to_num(prob_probe, nan=0.0).astype(np.float16))

        stats = _stats(frame["field"])
        cells = detect_cells(
            frame["field"],
            grid.lats,
            grid.lons,
            code=phase_code,
            cape=env["cape"] if env is not None else None,
            shear=env["shear"] if env is not None else None,
        )
        if prev_cells is not None:
            cells = cell_growth(prev_cells, cells)
        prev_cells = cells
        stats["cells"] = len(cells)
        stats["thunder_cells"] = sum(1 for c in cells if c["type"] == "thunder")
        stats["cell_types"] = {k: sum(1 for c in cells if c["type"] == k) for k in ("thunder", "shower", "rain", "snow", "mixed")}
        if cells:
            stats["top_cell"] = {k: cells[0][k] for k in ("lat", "lon", "max_dbz", "area_km2", "type", "label", "confidence")}
        if phase_code is not None:
            echo = np.isfinite(frame["field"]) & (frame["field"] >= DBZ_FLOOR)
            total = int(echo.sum())
            stats["snow_fraction"] = round(float((echo & (phase_code == phase_mod.SNOW)).sum()) / total, 2) if total else 0.0
            stats["mixed_fraction"] = round(float((echo & (phase_code == phase_mod.MIXED)).sum()) / total, 2) if total else 0.0
        if env is not None:
            idxs = grid.nearest_index(cells[0]["lat"], cells[0]["lon"]) if cells else (grid.ny // 2, grid.nx // 2)
            stats["severe"] = severe.severe_index(
                cells,
                float(env["cape"][idxs]),
                float(env["shear"][idxs]),
            )
        if frame["prob"] is not None:
            stats["prob30_max"] = round(float(np.nanmax(frame["prob"])), 2)
            stats["prob30_area_km2"] = int((frame["prob"] > 0.5).sum() * CELL_KM2)
        manifest_frames.append(
            {
                "id": frame["id"],
                "kind": frame["kind"],
                "time": frame["time"],
                "lead_min": frame["lead_min"],
                "tile_url": f"/tiles/{frame['id']}/{{z}}/{{x}}/{{y}}.png",
                "stats": stats,
                "cells": cells,
                "zoom_tiles": {str(z): v["tiles"] for z, v in zoom_info.items()},
            }
        )

    focus = None
    last = mosaics[-1]
    wet = np.isfinite(last) & (last >= 30.0)
    if wet.any():
        iy, ix = np.where(wet)
        cy = int(np.median(iy))
        cx = int(np.median(ix))
        lat_c = float(grid.lats[cy])
        lon_c = float(grid.lons[cx])
        focus = [
            [round(max(grid.lat_min, lat_c - 4.0), 2), round(max(grid.lon_min, lon_c - 7.0), 2)],
            [round(min(grid.lat_max, lat_c + 4.0), 2), round(min(grid.lon_max, lon_c + 7.0), 2)],
        ]

    phase_summary = None
    if phase_code is not None:
        echo = np.isfinite(mosaics[-1]) & (mosaics[-1] >= DBZ_FLOOR)
        total = int(echo.sum())
        phase_summary = {
            "snow_pct": round(100.0 * float((echo & (phase_code == phase_mod.SNOW)).sum()) / total, 1) if total else 0.0,
            "mixed_pct": round(100.0 * float((echo & (phase_code == phase_mod.MIXED)).sum()) / total, 1) if total else 0.0,
            "rain_pct": round(100.0 * float((echo & (phase_code == phase_mod.RAIN)).sum()) / total, 1) if total else 0.0,
            "wetbulb_min": round(float(np.nanmin(wet)), 1),
            "wetbulb_max": round(float(np.nanmax(wet)), 1),
        }

    manifest = {
        "generated_at": _iso(datetime.now(timezone.utc)),
        "tile_version": int(datetime.now(timezone.utc).timestamp()),
        "generation_seconds": round(time.time() - started, 1),
        "region": {
            "name": "Республика Саха (Якутия)",
            "bounds": [[54.0, 104.0], [74.0, 166.0]],
            "grid_step_deg": grid.step,
            "size": [grid.ny, grid.nx],
        },
        "stations": [],
        "coverage_pct": round(visibility_pct, 2),
        "phase": phase_summary,
        "env": {
            "available": env is not None,
            "t2m_min": round(float(np.nanmin(env["t2m"])), 1) if env is not None else None,
            "t2m_max": round(float(np.nanmax(env["t2m"])), 1) if env is not None else None,
            "cape_max": round(float(np.nanmax(env["cape"])), 0) if env is not None else None,
            "shear_max": round(float(np.nanmax(env["shear"])), 1) if env is not None else None,
        },
        "nowcast": {
            "method": method,
            "members": result["members"],
            "steps": NOWCAST_STEPS,
            "step_min": FRAME_MINUTES,
            "skill": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in last_skill.items()},
            "correction_weights": [round(float(x), 3) for x in result["correction"]],
        },
        "focus": focus,
        "frames": manifest_frames,
        "probe": {"step": PROBE_STEP, "value_scale": 1.0},
        "source": imerg.describe(),
        "cell_legend": TYPE_META,
        "echo_coverage_pct": round(echo_pct, 2),
    }

    manifest = _clean(manifest)
    out = Path(CLIENT).parent / "data" / "manifest.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")

    coarse = Grid(step=1.0)
    embedded = {
        "step": 1.0,
        "lat0": coarse.lat_min,
        "lon0": coarse.lon_min,
        "ny": coarse.ny,
        "nx": coarse.nx,
        "frames": {},
        "prob": {},
    }
    for frame in frames:
        arr = coarse.sample(frame["field"], coarse.lat2d, coarse.lon2d)
        embedded["frames"][frame["id"]] = [
            None if not np.isfinite(v) else round(float(v), 1) for v in arr.ravel()
        ]
        if phase_code is not None:
            cc = coarse.sample(phase_code.astype(np.float32), coarse.lat2d, coarse.lon2d)
            embedded.setdefault("phase", {})[frame["id"]] = [
                int(round(p)) if (np.isfinite(v) and v >= 5.0) else 0
                for v, p in zip(arr.ravel(), cc.ravel())
            ]
        if frame["prob"] is not None:
            pa = coarse.sample(frame["prob"], coarse.lat2d, coarse.lon2d)
            embedded["prob"][frame["id"]] = [round(float(v), 2) for v in pa.ravel()]

    env_payload = None
    if env is not None:
        ct = coarse.sample(env["t2m"], coarse.lat2d, coarse.lon2d)
        ch = coarse.sample(env["rh2m"], coarse.lat2d, coarse.lon2d)
        cw = coarse.sample(wet, coarse.lat2d, coarse.lon2d)
        cc = coarse.sample(env["cape"], coarse.lat2d, coarse.lon2d)
        cs = coarse.sample(env["shear"], coarse.lat2d, coarse.lon2d)
        env_payload = {
            "step": 1.0,
            "lat0": coarse.lat_min,
            "lon0": coarse.lon_min,
            "ny": coarse.ny,
            "nx": coarse.nx,
            "t2m": [round(float(v), 1) for v in ct.ravel()],
            "rh2m": [round(float(v), 0) for v in ch.ravel()],
            "wetbulb": [round(float(v), 1) for v in cw.ravel()],
            "cape": [round(float(v), 0) for v in cc.ravel()],
            "shear": [round(float(v), 1) for v in cs.ravel()],
        }
        prof = env.get("profile")
        if prof:
            env_payload["profile"] = {
                "step": prof["step"],
                "lat0": prof["lat0"],
                "lon0": prof["lon0"],
                "ny": prof["ny"],
                "nx": prof["nx"],
                "levels": prof["levels"],
                "t": [[round(float(v), 1) for v in row.ravel()] for row in prof["t"]],
                "u": [[round(float(v), 1) for v in row.ravel()] for row in prof["u"]],
                "v": [[round(float(v), 1) for v in row.ravel()] for row in prof["v"]],
            }

    payload = _clean({"manifest": manifest, "probe": embedded, "env": env_payload})
    (CLIENT / "data.js").write_text(
        "window.RADAR_STATE=" + json.dumps(payload, ensure_ascii=False, allow_nan=False) + ";\n",
        encoding="utf-8",
    )
    return manifest


if __name__ == "__main__":
    m = run()
    print(
        "frames",
        len(m["frames"]),
        "seconds",
        m["generation_seconds"],
        "coverage%",
        m["coverage_pct"],
        "skill",
        m["nowcast"]["skill"],
    )
