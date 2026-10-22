import sys; sys.path.insert(0, ".")
from datetime import datetime, timezone
import numpy as np
from radar.grid import Grid
from radar.sources import gfs

g = Grid()
f = gfs.fetch(g, datetime.now(timezone.utc))
if f is None:
    print("NO DATA")
else:
    for k, v in f.items():
        print(k, v.shape, round(float(np.nanmin(v)), 2), round(float(np.nanmax(v)), 2), round(float(np.nanmean(v)), 2))
