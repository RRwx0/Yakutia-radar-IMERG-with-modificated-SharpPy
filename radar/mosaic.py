from __future__ import annotations

import numpy as np
from scipy.ndimage import map_coordinates

from .config import Station
from .grid import Grid, azimuth_deg, haversine_km


def station_geometry(grid: Grid, station: Station) -> tuple[np.ndarray, np.ndarray]:
    r = haversine_km(station.lat, station.lon, grid.lat2d, grid.lon2d)
    az = azimuth_deg(station.lat, station.lon, grid.lat2d, grid.lon2d)
    return r, az


def project_ppi(grid: Grid, station: Station, dbz: np.ndarray, azimuth: np.ndarray, rng_km: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    r, az = station_geometry(grid, station)
    gate = float(rng_km[1] - rng_km[0])
    r_idx = (r - float(rng_km[0])) / gate
    a_idx = az % 360.0
    tiled = np.vstack([dbz, dbz[:1, :]])
    sample = map_coordinates(tiled, [a_idx.ravel(), r_idx.ravel()], order=1, mode="nearest").reshape(grid.shape)
    visible = r <= 238.0
    valid = visible & np.isfinite(sample) & (sample >= 2.0)
    return np.where(valid, sample, np.nan).astype(np.float32), r.astype(np.float32), visible


def build_mosaic(grid: Grid, scans: list[dict]) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    mosaic = np.full(grid.shape, np.nan, dtype=np.float32)
    coverage = np.zeros(grid.shape, dtype=np.uint16)
    visibility = np.zeros(grid.shape, dtype=np.uint16)
    nearest = np.full(grid.shape, np.inf, dtype=np.float32)

    for scan in scans:
        proj, dist, visible = project_ppi(grid, scan["station"], scan["dbz"], scan["azimuth"], scan["range"])
        valid = np.isfinite(proj)
        coverage += valid.astype(np.uint16)
        visibility += visible.astype(np.uint16)
        nearest = np.where(valid & (dist < nearest), dist, nearest)
        mosaic = np.where(valid, np.fmax(mosaic, proj), mosaic)

    mosaic = np.where(coverage > 0, mosaic, np.nan)
    return mosaic.astype(np.float32), coverage, nearest, visibility
