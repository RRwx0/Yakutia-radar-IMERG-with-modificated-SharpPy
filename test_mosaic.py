import sys
import time
from pathlib import Path

sys.path.insert(0, ".")

import numpy as np

from radar.config import STATIONS, VOLUMES
from radar.grid import Grid
from radar.mosaic import build_mosaic
from radar.qc import clean_ppi
from radar.sources.netcdf_source import read_volume

if __name__ == "__main__":
    grid = Grid()
    files = sorted(VOLUMES.glob("*.nc"))
    print("volumes", len(files))
    t0 = time.time()
    scans = []
    for path in files:
        vol = read_volume(path)
        sid = vol["meta"]["station_id"]
        station = next(s for s in STATIONS if s.id == sid)
        dbz, stats = clean_ppi(vol["dbz"], vol["range"])
        scans.append(
            {
                "station": station,
                "dbz": dbz,
                "azimuth": vol["azimuth"],
                "range": vol["range"],
                "time": vol["time"],
                "qc": stats,
            }
        )
        print(sid, "qc", {k: round(v, 2) for k, v in stats.items()}, "max", round(float(np.nanmax(dbz)), 1))

    mosaic, coverage, nearest, visibility = build_mosaic(grid, scans)
    print("mosaic", mosaic.shape, "seconds", round(time.time() - t0, 2))
    print("radar visibility %", round(100 * (visibility > 0).mean(), 1))
    print("precip coverage %", round(100 * (coverage > 0).mean(), 1), "max dbz", round(float(np.nanmax(mosaic)), 1))
    print("cells >30 dBZ", int(np.nansum(mosaic > 30)))
