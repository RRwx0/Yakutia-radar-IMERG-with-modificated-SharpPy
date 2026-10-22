from __future__ import annotations

import numpy as np

from .config import LAT_MAX, LAT_MIN, LON_MAX, LON_MIN, STEP

EARTH_KM = 6371.0
DEG_KM = 111.32


class Grid:
    def __init__(
        self,
        lon_min: float = LON_MIN,
        lon_max: float = LON_MAX,
        lat_min: float = LAT_MIN,
        lat_max: float = LAT_MAX,
        step: float = STEP,
    ) -> None:
        self.lon_min = lon_min
        self.lon_max = lon_max
        self.lat_min = lat_min
        self.lat_max = lat_max
        self.step = step
        self.lons = np.arange(lon_min, lon_max + step / 2, step)
        self.lats = np.arange(lat_min, lat_max + step / 2, step)
        self.ny = self.lats.size
        self.nx = self.lons.size
        self.lon2d, self.lat2d = np.meshgrid(self.lons, self.lats)

    @property
    def shape(self) -> tuple[int, int]:
        return (self.ny, self.nx)

    def sample(self, field: np.ndarray, lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
        fx = (np.asarray(lon) - self.lon_min) / self.step
        fy = (np.asarray(lat) - self.lat_min) / self.step
        x0 = np.floor(fx).astype(np.int64)
        y0 = np.floor(fy).astype(np.int64)
        tx = fx - x0
        ty = fy - y0
        x0 = np.clip(x0, 0, self.nx - 2)
        y0 = np.clip(y0, 0, self.ny - 2)
        x1 = x0 + 1
        y1 = y0 + 1
        out = (
            field[y0, x0] * (1 - tx) * (1 - ty)
            + field[y0, x1] * tx * (1 - ty)
            + field[y1, x0] * (1 - tx) * ty
            + field[y1, x1] * tx * ty
        )
        outside = (lon < self.lon_min) | (lon > self.lon_max) | (lat < self.lat_min) | (lat > self.lat_max)
        if np.any(outside):
            out = np.where(outside, np.nan, out)
        return out

    def nearest_index(self, lat: float, lon: float) -> tuple[int, int]:
        iy = int(round((lat - self.lat_min) / self.step))
        ix = int(round((lon - self.lon_min) / self.step))
        iy = max(0, min(self.ny - 1, iy))
        ix = max(0, min(self.nx - 1, ix))
        return iy, ix


def haversine_km(lat1, lon1, lat2, lon2):
    lat1 = np.radians(lat1)
    lat2 = np.radians(lat2)
    dlat = lat2 - lat1
    dlon = np.radians(np.asarray(lon2) - np.asarray(lon1))
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_KM * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def azimuth_deg(lat1, lon1, lat2, lon2):
    lat1r = np.radians(lat1)
    lat2r = np.radians(lat2)
    dlon = np.radians(np.asarray(lon2) - np.asarray(lon1))
    y = np.sin(dlon) * np.cos(lat2r)
    x = np.cos(lat1r) * np.sin(lat2r) - np.sin(lat1r) * np.cos(lat2r) * np.cos(dlon)
    return (np.degrees(np.arctan2(y, x)) + 360.0) % 360.0


def beam_height_km(range_km, antenna_m: float = 120.0) -> np.ndarray:
    r = np.asarray(range_km, dtype=float)
    return (antenna_m / 1000.0) + r**2 / (2 * 8500.0)
