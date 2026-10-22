from __future__ import annotations

import math
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
from scipy.ndimage import map_coordinates

from ..config import CACHE, LAT_MAX, LAT_MIN, LON_MAX, LON_MIN
from ..grid import Grid

GIBS = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/IMERG_Precipitation_Rate_30min/default/"
MATRIX = "GoogleMapsCompatible_Level6"
ZOOM = 5
TILE = 256
STEP_MIN = 30

PALETTE = np.array(
    [
        [164, 248, 241, 0.2],
        [109, 184, 225, 0.7],
        [63, 143, 210, 1.2],
        [0, 131, 62, 2.2],
        [0, 151, 31, 4.0],
        [143, 214, 0, 7.0],
        [253, 203, 0, 12.0],
        [255, 152, 16, 17.0],
        [255, 101, 25, 25.0],
        [255, 45, 45, 40.0],
        [206, 0, 0, 55.0],
        [150, 0, 60, 65.0],
        [212, 0, 160, 75.0],
    ],
    dtype=np.float32,
)


def _world_px(lat, lon, z=ZOOM):
    n = TILE * (2**z)
    x = (np.asarray(lon, dtype=np.float64) + 180.0) / 360.0 * n
    lat_r = np.radians(np.asarray(lat, dtype=np.float64))
    y = (1.0 - np.log(np.tan(lat_r) + 1.0 / np.cos(lat_r)) / np.pi) / 2.0 * n
    return x, y


def tile_bounds(z=ZOOM):
    x0, y0 = _world_px(LAT_MAX, LON_MIN, z)
    x1, y1 = _world_px(LAT_MIN, LON_MAX, z)
    return int(x0 // TILE), int(x1 // TILE), int(y0 // TILE), int(y1 // TILE)


def _safe(iso: str) -> str:
    return iso.replace(":", "")


def _url(iso: str, z: int, x: int, y: int) -> str:
    return f"{GIBS}{iso}/{MATRIX}/{z}/{y}/{x}.png"


def _get(url: str, path: Path) -> bool:
    if path.exists() and path.stat().st_size > 0:
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        req = Request(url, headers={"User-Agent": "YakutiaRadar/1.0"})
        with urlopen(req, timeout=25) as r, open(path, "wb") as fh:
            fh.write(r.read())
        return True
    except Exception:
        return False


def latest_time(lag_h: int = 7) -> datetime:
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    end = now - timedelta(hours=lag_h)
    end -= timedelta(minutes=end.minute % STEP_MIN)
    x0, _x1, y0, _y1 = tile_bounds()
    for _ in range(10):
        iso = end.strftime("%Y-%m-%dT%H:%M:00Z")
        probe = CACHE / "imerg" / _safe(iso) / f"{ZOOM}_{x0}_{y0}.png"
        if _get(_url(iso, ZOOM, x0, y0), probe) and probe.stat().st_size > 200:
            return end
        end -= timedelta(minutes=STEP_MIN)
    return end


def frames(n: int = 12) -> list[datetime]:
    end = latest_time()
    return [end - timedelta(minutes=STEP_MIN * (n - 1 - i)) for i in range(n)]


def _mosaic(iso: str) -> tuple[np.ndarray, int, int]:
    x0, x1, y0, y1 = tile_bounds()
    nx = (x1 - x0 + 1) * TILE
    ny = (y1 - y0 + 1) * TILE
    canvas = np.zeros((ny, nx, 4), dtype=np.uint8)

    jobs = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                path = CACHE / "imerg" / _safe(iso) / f"{ZOOM}_{tx}_{ty}.png"
                jobs.append((pool.submit(_get, _url(iso, ZOOM, tx, ty), path), tx, ty, path))

    from PIL import Image

    for future, tx, ty, path in jobs:
        if not future.result() or not path.exists() or path.stat().st_size < 200:
            continue
        try:
            tile = np.asarray(Image.open(path).convert("RGBA"))
        except Exception:
            continue
        if tile.shape[0] != TILE:
            continue
        canvas[(ty - y0) * TILE : (ty - y0 + 1) * TILE, (tx - x0) * TILE : (tx - x0 + 1) * TILE] = tile
    return canvas, x0, y0


def _decode(canvas: np.ndarray) -> np.ndarray:
    rgb = canvas[..., :3].reshape(-1, 3).astype(np.int16)
    alpha = canvas[..., 3].ravel()
    uniq, inv = np.unique(rgb, axis=0, return_inverse=True)
    pal = PALETTE[:, :3].astype(np.int16)
    dist = ((uniq[:, None, :] - pal[None, :, :]) ** 2).sum(axis=2)
    nearest = dist.argmin(axis=1)
    values = PALETTE[nearest, 3].astype(np.float32)
    rate = values[inv].reshape(canvas.shape[0], canvas.shape[1])
    rate[alpha.reshape(canvas.shape[:2]) < 20] = 0.0
    return rate


def fetch_field(grid: Grid, when: datetime) -> np.ndarray:
    iso = when.strftime("%Y-%m-%dT%H:%M:00Z")
    canvas, x0, y0 = _mosaic(iso)
    rate = _decode(canvas)
    if rate.max() <= 0:
        return np.full(grid.shape, np.nan, dtype=np.float32)

    mask = (rate > 0.05).astype(np.float32)
    gx, gy = _world_px(grid.lat2d, grid.lon2d)
    px = gx - x0 * TILE - 0.5
    py = gy - y0 * TILE - 0.5
    sampled = map_coordinates(rate, [py.ravel(), px.ravel()], order=1, mode="constant", cval=0.0).reshape(grid.shape)
    covered = map_coordinates(mask, [py.ravel(), px.ravel()], order=1, mode="constant", cval=0.0).reshape(grid.shape)
    sampled = np.where(covered > 0.4, sampled, np.nan)
    sampled = np.where(sampled < 0.1, np.nan, sampled)

    with np.errstate(divide="ignore", invalid="ignore"):
        dbz = 10.0 * np.log10(200.0 * np.power(sampled, 1.6))
    return np.where(np.isfinite(dbz) & (dbz >= 5.0), dbz, np.nan).astype(np.float32)


def describe() -> dict:
    return {
        "id": "imerg",
        "name": "GPM IMERG Early Run",
        "provider": "NASA / JAXA",
        "resolution_km": 11.0,
        "step_min": STEP_MIN,
        "latency_h": 7,
        "tile_zoom": ZOOM,
        "url": "https://gibs.earthdata.nasa.gov/",
    }
