import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, ".")

import numpy as np

from radar.config import STATIONS, VOLUMES
from radar.grid import Grid
from radar.mosaic import build_mosaic
from radar.nowcast import advect, estimate_flow, forecast, skill
from radar.qc import clean_ppi
from radar.sources.netcdf_source import read_volume

if __name__ == "__main__":
    grid = Grid()
    grouped = defaultdict(list)
    for path in sorted(VOLUMES.glob("*.nc")):
        vol = read_volume(path)
        station = next(s for s in STATIONS if s.id == vol["meta"]["station_id"])
        dbz, _ = clean_ppi(vol["dbz"], vol["range"])
        grouped[vol["time"]].append(
            {"station": station, "dbz": dbz, "azimuth": vol["azimuth"], "range": vol["range"]}
        )

    times = sorted(grouped)
    mosaics = [build_mosaic(grid, grouped[t])[0] for t in times]
    print("mosaics", len(mosaics), mosaics[0].shape)

    t0 = time.time()
    u, v = estimate_flow(mosaics[0], mosaics[1])
    adv = advect(mosaics[0], u, v)
    print("flow mean px", round(float(np.hypot(u, v).mean()), 2), "seconds", round(time.time() - t0, 2))
    print("skill", skill(mosaics[0], adv, mosaics[1]))

    t0 = time.time()
    res = forecast(mosaics, steps=6, members=5)
    print("forecast seconds", round(time.time() - t0, 2), "frames", res["frames"].shape)
    print("prob30 at +60", round(float(res["prob30"][-1].max()), 2), "max dbz", round(float(res["frames"][-1].max()), 1))
