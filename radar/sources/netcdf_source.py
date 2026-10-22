from __future__ import annotations

from pathlib import Path

import numpy as np


def _attr(ds, name, default=None):
    value = getattr(ds, name, default)
    if isinstance(value, bytes):
        value = value.decode("utf-8", "replace").strip("\x00")
    if isinstance(value, tuple) and value and isinstance(value[0], bytes):
        value = value[0].decode("utf-8", "replace").strip("\x00")
    return value


def read_volume(path: Path) -> dict:
    try:
        from netCDF4 import Dataset

        with Dataset(str(path)) as ds:
            dbz = np.array(ds.variables["DBZ"][:], dtype=np.float32)
            az = np.array(ds.variables["azimuth"][:], dtype=np.float32)
            rng = np.array(ds.variables["range"][:], dtype=np.float32)
            t = float(np.array(ds.variables["time"][:]).ravel()[0])
            meta = {
                "station_id": _attr(ds, "station_id", path.stem.split("_")[0]),
                "station_name": _attr(ds, "station_name", ""),
                "lat": float(_attr(ds, "latitude", 0.0)),
                "lon": float(_attr(ds, "longitude", 0.0)),
                "range_km": float(_attr(ds, "range_km", 250.0)),
            }
    except Exception:
        from scipy.io import netcdf_file

        with netcdf_file(str(path), "r", mmap=False) as ds:
            dbz = np.array(ds.variables["DBZ"][:], dtype=np.float32)
            az = np.array(ds.variables["azimuth"][:], dtype=np.float32)
            rng = np.array(ds.variables["range"][:], dtype=np.float32)
            t = float(np.array(ds.variables["time"][:]).ravel()[0])
            meta = {
                "station_id": _attr(ds, "station_id", path.stem.split("_")[0]),
                "station_name": _attr(ds, "station_name", ""),
                "lat": float(_attr(ds, "latitude", 0.0)),
                "lon": float(_attr(ds, "longitude", 0.0)),
                "range_km": float(_attr(ds, "range_km", 250.0)),
            }
    if dbz.ndim == 3:
        dbz = dbz[0]
    dbz = np.where(dbz < -100, np.nan, dbz)
    return {"dbz": dbz, "azimuth": az, "range": rng, "time": t, "meta": meta}
