import sys, time
sys.path.insert(0, ".")
import numpy as np
from radar.grid import Grid
from radar.sources import imerg

grid = Grid()
t0 = time.time()
when = imerg.latest_time()
print("latest", when.isoformat(), "probe", round(time.time()-t0,1))
t0 = time.time()
f = imerg.fetch_field(grid, when)
print("field", f.shape, "seconds", round(time.time()-t0,1))
print("max", round(float(np.nanmax(f)),1), "wet%", round(100*float(np.isfinite(f).mean()),2))
