from __future__ import annotations

import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from scipy.ndimage import map_coordinates

from ..config import CACHE
from ..grid import Grid

BASE = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl"
GFS_CACHE = CACHE / "gfs"
PROFILE_LEVELS = (850, 700, 500, 300)
PROFILE_STEP = 2.0


def _params(date: str, cycle: str, step: int) -> str:
    levels = "".join(
        f"&lev_{lev}_mb=on&var_TMP=on&var_UGRD=on&var_VGRD=on" for lev in PROFILE_LEVELS
    )
    return (
        f"?file=gfs.t{cycle}z.pgrb2.0p25.f{step:03d}"
        "&lev_2_m_above_ground=on&var_TMP=on"
        "&lev_2_m_above_ground=on&var_RH=on"
        "&lev_surface=on&var_CAPE=on"
        "&lev_10_m_above_ground=on&var_UGRD=on&var_VGRD=on"
        f"{levels}"
        "&subregion=&leftlon=100&rightlon=170&toplat=76&bottomlat=50"
        f"&dir=%2Fgfs.{date}%2F{cycle}%2Fatmos"
    )


def _download(when: datetime) -> Path | None:
    GFS_CACHE.mkdir(parents=True, exist_ok=True)
    when = when.astimezone(timezone.utc)
    for attempt in range(8):
        run = when - timedelta(hours=6 * attempt)
        cycle = (run.hour // 6) * 6
        date = run.strftime("%Y%m%d")
        path = GFS_CACHE / f"gfs_{date}_{cycle:02d}_v4.grib2"
        if path.exists() and path.stat().st_size > 10000:
            return path
        url = BASE + _params(date, f"{cycle:02d}", 0)
        try:
            with urllib.request.urlopen(url, timeout=90) as r, open(path, "wb") as fh:
                fh.write(r.read())
            if path.stat().st_size > 10000:
                return path
        except urllib.error.HTTPError:
            continue
        except Exception:
            continue
    return None


def _sample(ds, grid: Grid) -> np.ndarray:
    lat = np.asarray(ds["latitude"].values, dtype=float)
    lon = np.asarray(ds["longitude"].values, dtype=float)
    order = np.argsort(lat)
    data = np.asarray(ds.values, dtype=np.float32)[order, :]
    lat_s = lat[order]
    fy = (grid.lat2d - lat_s[0]) / (lat_s[1] - lat_s[0])
    fx = (grid.lon2d - lon[0]) / (lon[1] - lon[0])
    return map_coordinates(data, [fy.ravel(), fx.ravel()], order=1, mode="nearest").reshape(grid.shape)


def _profile_from(files, prof_grid: Grid) -> dict | None:
    levels: list[int] = []
    temps: list[np.ndarray] = []
    us: list[np.ndarray] = []
    vs: list[np.ndarray] = []
    for ds in files:
        if "isobaricInhPa" not in ds.coords or "t" not in ds.variables:
            continue
        have = [int(v) for v in np.atleast_1d(ds["isobaricInhPa"].values)]
        for lev in PROFILE_LEVELS:
            if lev not in have or lev in levels:
                continue
            sel = ds.sel(isobaricInhPa=lev) if len(have) > 1 else ds
            t = _sample(sel["t"].squeeze(), prof_grid) - 273.15
            u = _sample(sel["u"].squeeze(), prof_grid) if "u" in sel else np.zeros_like(t)
            v = _sample(sel["v"].squeeze(), prof_grid) if "v" in sel else np.zeros_like(t)
            levels.append(lev)
            temps.append(t)
            us.append(u)
            vs.append(v)
    if not levels:
        return None
    order = np.argsort(levels)[::-1]
    return {
        "levels": [levels[i] for i in order],
        "t": np.stack([temps[i] for i in order]),
        "u": np.stack([us[i] for i in order]),
        "v": np.stack([vs[i] for i in order]),
        "lat0": prof_grid.lat_min,
        "lon0": prof_grid.lon_min,
        "step": prof_grid.step,
        "ny": prof_grid.ny,
        "nx": prof_grid.nx,
    }


def fetch(grid: Grid, when: datetime) -> dict | None:
    path = _download(when)
    if path is None:
        return None
    key = path.stem.replace("gfs_", "fields_v4_")
    cached = GFS_CACHE / f"{key}.npz"
    if cached.exists():
        with np.load(cached) as z:
            prof = None
            if "prof_levels" in z.files:
                prof = {
                    "levels": z["prof_levels"].tolist(),
                    "t": z["prof_t"],
                    "u": z["prof_u"],
                    "v": z["prof_v"],
                    "lat0": float(z["prof_lat0"]),
                    "lon0": float(z["prof_lon0"]),
                    "step": float(z["prof_step"]),
                    "ny": int(z["prof_ny"]),
                    "nx": int(z["prof_nx"]),
                }
            return {"t2m": z["t2m"], "rh2m": z["rh2m"], "cape": z["cape"], "shear": z["shear"], "profile": prof}
    try:
        import cfgrib

        sets = cfgrib.open_datasets(str(path))
        out: dict[str, np.ndarray] = {}
        for ds in sets:
            if "t2m" in ds.variables:
                out["t2m"] = _sample(ds["t2m"], grid) - 273.15
            if "r2" in ds.variables:
                out["rh2m"] = _sample(ds["r2"], grid)
            if "cape" in ds.variables:
                out["cape"] = _sample(ds["cape"], grid)
            if "u10" in ds.variables and "v10" in ds.variables:
                out["u10"] = _sample(ds["u10"], grid)
                out["v10"] = _sample(ds["v10"], grid)
            if "u" in ds.variables and "v" in ds.variables and "isobaricInhPa" in ds.coords:
                levels = np.atleast_1d(ds["isobaricInhPa"].values)
                if np.any(np.isclose(levels, 500)):
                    sel = ds.sel(isobaricInhPa=500) if levels.size > 1 else ds
                    out["u500"] = _sample(sel["u"].squeeze(), grid)
                    out["v500"] = _sample(sel["v"].squeeze(), grid)

        if "t2m" not in out:
            return None
        prof = _profile_from(sets, Grid(step=PROFILE_STEP))
        rh = out.get("rh2m", np.full_like(out["t2m"], 75.0))
        cape = out.get("cape", np.zeros_like(out["t2m"]))
        if "u500" in out and "u10" in out:
            shear = np.hypot(out["u500"] - out["u10"], out["v500"] - out["v10"])
        else:
            shear = np.zeros_like(out["t2m"])

        save = {"t2m": out["t2m"], "rh2m": rh, "cape": cape, "shear": shear}
        if prof is not None:
            save.update(
                {
                    "prof_levels": np.array(prof["levels"], dtype=np.int16),
                    "prof_t": prof["t"].astype(np.float32),
                    "prof_u": prof["u"].astype(np.float32),
                    "prof_v": prof["v"].astype(np.float32),
                    "prof_lat0": prof["lat0"],
                    "prof_lon0": prof["lon0"],
                    "prof_step": prof["step"],
                    "prof_ny": prof["ny"],
                    "prof_nx": prof["nx"],
                }
            )
        np.savez_compressed(cached, **save)
        return {"t2m": out["t2m"], "rh2m": rh, "cape": cape, "shear": shear, "profile": prof}
    except Exception:
        return None
