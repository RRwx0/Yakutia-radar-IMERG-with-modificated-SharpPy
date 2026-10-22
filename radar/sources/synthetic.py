from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

import numpy as np
from netCDF4 import Dataset

from ..config import STATIONS, Station
from ..grid import Grid, DEG_KM

U_MS = 9.0
V_MS = 2.0


@dataclass(frozen=True)
class Cell:
    lon: float
    lat: float
    amp: float
    sigma_km: float
    peak_min: float
    life_min: float


CELLS = (
    Cell(119.4, 60.15, 54.0, 46.0, 55.0, 80.0),
    Cell(120.8, 60.95, 46.0, 30.0, 75.0, 60.0),
    Cell(122.2, 60.35, 41.0, 38.0, 40.0, 90.0),
    Cell(124.6, 59.70, 36.0, 52.0, 25.0, 95.0),
    Cell(127.9, 61.10, 33.0, 44.0, 95.0, 70.0),
    Cell(130.1, 61.95, 28.0, 36.0, 110.0, 55.0),
)

STRATIFORM = Cell(123.0, 60.6, 14.0, 260.0, 60.0, 200.0)


def _noise(grid: Grid, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    raw = rng.standard_normal(grid.shape).astype(np.float32)
    k = 9
    pad = np.pad(raw, k, mode="reflect")
    acc = np.zeros_like(raw)
    for dy in (-k // 2, 0, k // 2):
        for dx in (-k // 2, 0, k // 2):
            acc += pad[k + dy : k + dy + grid.ny, k + dx : k + dx + grid.nx]
    acc /= 9.0
    acc -= acc.mean()
    acc /= max(1e-6, acc.std())
    return acc


def _cell_field(grid: Grid, cell: Cell, t_min: float) -> np.ndarray:
    dx_km = (grid.lon2d - cell.lon) * DEG_KM * np.cos(np.radians(cell.lat))
    dy_km = (grid.lat2d - cell.lat) * DEG_KM
    dx_km = dx_km - (U_MS * 60.0 * t_min) / 1000.0
    dy_km = dy_km - (V_MS * 60.0 * t_min) / 1000.0
    d2 = dx_km**2 + dy_km**2
    amp = cell.amp * math.exp(-(((t_min - cell.peak_min) / cell.life_min) ** 2))
    if amp < 0.5:
        return np.zeros(grid.shape, dtype=np.float32)
    return (amp * np.exp(-d2 / (2 * cell.sigma_km**2))).astype(np.float32)


def truth_field(grid: Grid, t_min: float, seed: int = 7) -> np.ndarray:
    field = _cell_field(grid, STRATIFORM, t_min)
    for cell in CELLS:
        field = np.maximum(field, _cell_field(grid, cell, t_min))
    texture = _noise(grid, seed)
    shift = int(round(t_min / 10.0))
    texture = np.roll(texture, shift, axis=1)
    field = field + texture * np.clip(field / 40.0, 0.0, 1.0) * 4.5
    field = np.where(field < 2.0, 0.0, field)
    return np.clip(field, 0.0, 68.0).astype(np.float32)


def _polar_coords(station: Station, az: np.ndarray, rng: np.ndarray):
    az_rad = np.radians(az)[:, None]
    r = rng[None, :]
    lat = station.lat + (r * np.cos(az_rad)) / DEG_KM
    lon = station.lon + (r * np.sin(az_rad)) / (DEG_KM * np.cos(np.radians(station.lat)))
    return lat, lon


def simulate_ppi(station: Station, grid: Grid, t_min: float, seed: int = 11) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed + int(t_min) + (0 if station.id == "yakutsk" else 1000))
    az = np.arange(0.0, 360.0, 1.0)
    rng_km = np.arange(1.0, station.range_km + 0.5, station.gate_km)

    field = _truth_cache(grid, t_min)
    acc = np.zeros((az.size, rng_km.size), dtype=np.float32)
    weight = 0.0
    for offset, w in ((-0.5, 0.2), (-0.25, 0.3), (0.0, 1.0), (0.25, 0.3), (0.5, 0.2)):
        lat, lon = _polar_coords(station, az + offset, rng_km)
        sample = grid.sample(field, lat, lon)
        sample = np.nan_to_num(sample, nan=0.0)
        acc += sample.astype(np.float32) * w
        weight += w
    dbz = acc / weight

    z = np.power(10.0, (dbz - 30.0) / 10.0)
    atten = np.cumsum(0.0009 * z, axis=1) * station.gate_km
    dbz = dbz - np.clip(atten, 0.0, 18.0)

    dbz = dbz + rng.normal(0.0, 0.55 + rng_km[None, :] * 0.006, dbz.shape)

    clutter_az = rng.choice(az.size, size=26, replace=False)
    for a in clutter_az:
        span = rng.integers(3, 9)
        dbz[a : a + span, 1:14] = rng.uniform(34, 58, size=(min(span, az.size - a), 13))

    empty = rng.choice(az.size, size=8, replace=False)
    dbz[empty, :] = np.nan
    dbz[:, rng_km > 238] = np.nan
    dbz = np.where(dbz < 4.0, np.nan, dbz)
    return az.astype(np.float32), rng_km.astype(np.float32), dbz.astype(np.float32)


def write_volume(path, station: Station, when: datetime, az, rng_km, dbz) -> None:
    from scipy.io import netcdf_file

    with netcdf_file(str(path), "w", version=2) as ds:
        ds.createDimension("azimuth", az.size)
        ds.createDimension("range", rng_km.size)
        ds.createDimension("time", 1)
        v = ds.createVariable("DBZ", "f4", ("time", "azimuth", "range"))
        v.units = "dBZ"
        v.long_name = "Equivalent radar reflectivity factor"
        v[:] = dbz[None, :, :].astype("float32")
        a = ds.createVariable("azimuth", "f4", ("azimuth",))
        a.units = "degrees"
        r = ds.createVariable("range", "f4", ("range",))
        r.units = "km"
        t = ds.createVariable("time", "f8", ("time",))
        t.units = "seconds since 1970-01-01 00:00:00 UTC"
        a[:] = az
        r[:] = rng_km
        t[:] = float(when.timestamp())
        ds.station_id = station.id
        ds.station_name = station.id
        ds.latitude = station.lat
        ds.longitude = station.lon
        ds.range_km = station.range_km
        ds.beam_width_deg = station.beam_deg
        ds.instrument = "DMRL-S (simulated volume, C-band)"
        ds.history = f"generated {datetime.utcnow().isoformat()}Z"


def generate_series(grid: Grid, times, out_dir) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = []
    for i, when in enumerate(times):
        t_min = i * 10.0
        for station in STATIONS:
            az, rng_km, dbz = simulate_ppi(station, grid, t_min)
            name = f"{station.id}_{when:%Y%m%dT%H%M}.nc"
            write_volume(out_dir / name, station, when, az, rng_km, dbz)
            meta.append(
                {
                    "station": station.id,
                    "name": station.name,
                    "time": when.isoformat().replace("+00:00", "Z"),
                    "file": name,
                    "valid_gates": int(np.isfinite(dbz).sum()),
                    "max_dbz": float(np.nanmax(dbz)) if np.isfinite(dbz).any() else None,
                }
            )
    return meta


_TRUTH_CACHE: dict[tuple[int, int], np.ndarray] = {}


def _truth_cache(grid: Grid, t_min: float) -> np.ndarray:
    key = (id(grid), int(round(t_min)))
    if key not in _TRUTH_CACHE:
        _TRUTH_CACHE[key] = truth_field(grid, t_min)
    return _TRUTH_CACHE[key]
