from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.ndimage import map_coordinates

from ..config import DATA
from ..grid import Grid

IR_DIR = DATA / "ir"


def load(grid: Grid) -> tuple[np.ndarray, dict] | None:
    """Optional IR brightness temperature feed: data/ir/*.npz with bt, lat, lon.

    The site has no IR satellite ingest by default, so this returns None and the
    UI honestly reports that cold-ring detection has no input field.
    """
    if not IR_DIR.exists():
        return None
    files = sorted(IR_DIR.glob("*.npz"))
    if not files:
        return None
    path: Path = files[-1]
    try:
        with np.load(path) as z:
            bt = np.asarray(z["bt"], dtype=np.float32)
            lat = np.asarray(z["lat"], dtype=float)
            lon = np.asarray(z["lon"], dtype=float)
    except Exception:
        return None
    if bt.ndim != 2 or lat.ndim != 1 or lon.ndim != 1:
        return None
    order = np.argsort(lat)
    bt = bt[order, :]
    lat_s = lat[order]
    fy = (grid.lat2d - lat_s[0]) / (lat_s[1] - lat_s[0])
    fx = (grid.lon2d - lon[0]) / (lon[1] - lon[0])
    sampled = map_coordinates(bt, [fy.ravel(), fx.ravel()], order=1, mode="nearest").reshape(grid.shape)
    return sampled.astype(np.float32), {"file": path.name, "lat": [float(lat_s[0]), float(lat_s[-1])], "lon": [float(lon[0]), float(lon[-1])]}
