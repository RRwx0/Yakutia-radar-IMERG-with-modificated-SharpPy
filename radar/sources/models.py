from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import requests

from ..config import CACHE
from ..grid import Grid

MODELS = {
    "gfs": ("GFS (NOAA)", "онлайн", "https://nomads.ncep.noaa.gov"),
    "ecmwf": ("ECMWF IFS", "через Open-Meteo", "https://api.open-meteo.com"),
    "icon": ("ICON (DWD)", "через Open-Meteo", "https://api.open-meteo.com"),
    "msm": ("MSM (Япония)", "через Open-Meteo", "https://api.open-meteo.com"),
}
OPENMETEO_KEYS = {"ecmwf": "ecmwf_ifs025", "icon": "icon_seamless", "msm": "jma_msm"}

GFS_STEP_MIN = 60
MODEL_TILE_ZOOM = 4

_cache: dict[str, dict] = {}


def _zr(rate: np.ndarray) -> np.ndarray:
    rate = np.asarray(rate, dtype=np.float32)
    with np.errstate(divide="ignore", invalid="ignore"):
        dbz = 10.0 * np.log10(200.0 * np.power(rate * 3600.0, 1.6))
    return np.where(np.isfinite(dbz) & (dbz >= 5.0), dbz, np.nan).astype(np.float32)


def _nomads_latest() -> str:
    now = datetime.now(timezone.utc)
    for back in range(6):
        run = now - timedelta(hours=6 * back)
        cycle = (run.hour // 6) * 6
        date = run.strftime("%Y%m%d")
        probe = (
            f"https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl?file=gfs.t{cycle:02d}z.pgrb2.0p25.f000"
            f"&lev_surface=on&var_PRATE=on&subregion=&leftlon=104&rightlon=166&toplat=74&bottomlat=54"
            f"&dir=%2Fgfs.{date}%2F{cycle:02d}%2Fatmos"
        )
        try:
            r = requests.get(probe, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
            if r.status_code == 200 and len(r.content) > 1000:
                return f"{date}_{cycle:02d}"
        except Exception:
            continue
    return ""


def fetch_gfs(grid: Grid) -> dict | None:
    stamp = _nomads_latest()
    if not stamp:
        return None
    key = f"gfs:{stamp}"
    if key in _cache:
        return _cache[key]
    date, cycle = stamp.split("_")
    url = (
        f"https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl?file=gfs.t{cycle}z.pgrb2.0p25.f000"
        f"&lev_surface=on&var_PRATE=on&subregion=&leftlon=104&rightlon=166&toplat=74&bottomlat=54"
        f"&dir=%2Fgfs.{date}%2F{cycle}%2Fatmos"
    )
    try:
        import cfgrib
        from scipy.ndimage import map_coordinates

        path = CACHE / f"model_prate_{stamp}.grb2"
        path.parent.mkdir(parents=True, exist_ok=True)
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=120)
        if r.status_code != 200 or len(r.content) < 1000:
            return None
        path.write_bytes(r.content)
        ds = cfgrib.open_datasets(str(path))[0]
        lat = np.asarray(ds["latitude"].values, float)
        lon = np.asarray(ds["longitude"].values, float)
        rate = np.asarray(ds["prate"].values, np.float32)
        if lat[0] > lat[-1]:
            rate = rate[::-1, :]
            lat = lat[::-1]
        fy = (grid.lat2d - lat[0]) / (lat[1] - lat[0])
        fx = (grid.lon2d - lon[0]) / (lon[1] - lon[0])
        sampled = map_coordinates(rate, [fy.ravel(), fx.ravel()], order=1, mode="nearest").reshape(grid.shape)
        field = _zr(sampled)
    except Exception:
        return None
    result = {
        "field": field,
        "init": f"{date} {cycle}:00Z",
        "valid": f"{date} {cycle}:00Z",
        "model": "gfs",
        "name": MODELS["gfs"][0],
    }
    _cache[key] = result
    return result


def fetch_openmeteo(grid: Grid, key: str) -> dict | None:
    if key not in OPENMETEO_KEYS:
        return None
    model_code = OPENMETEO_KEYS[key]
    now = datetime.now(timezone.utc)
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": 64.0,
                "longitude": 135.0,
                "hourly": "precipitation",
                "models": model_code,
                "forecast_days": 1,
                "timezone": "UTC",
            },
            timeout=25,
        )
        r.raise_for_status()
        js = r.json()
        h = js["hourly"]
        vals = h["precipitation"]
        stamp = h["time"][0] if h["time"] else ""
    except Exception:
        return None
    grid_lats, grid_lons = grid.lat2d, grid.lon2d
    # Open-Meteo отдаёт точку, а не сетку: строим крупно-зернистое поле только
    # если API вернёт сетку (в данном продукте — нет). Честный fallback.
    field = np.full(grid.shape, np.nan, dtype=np.float32)
    try:
        rate = float(max(vals or [0.0]))
        if rate > 0:
            field = np.where(
                (grid_lats > 54) & (grid_lats < 74) & (grid_lons > 104) & (grid_lons < 166),
                rate,
                np.nan,
            )
            field = _zr(np.nan_to_num(field, nan=0.0))
            field[field < 5] = np.nan
    except Exception:
        return None
    return {
        "field": field,
        "init": stamp,
        "valid": stamp,
        "model": key,
        "name": MODELS[key][0],
        "note": "Open-Meteo не отдаёт сетку осадков; поле — точечная оценка. Установите API-ключ для полной карты",
    }


def fetch(grid: Grid, key: str) -> dict | None:
    if key == "gfs":
        return fetch_gfs(grid)
    return fetch_openmeteo(grid, key)


def describe() -> dict:
    return MODELS