import sys
sys.path.insert(0, ".")
import numpy as np
from radar.grid import Grid
from radar.sources import imerg
from radar.nowcast import advect

grid = Grid()
ts = imerg.frames(2)
a = imerg.fetch_field(grid, ts[0]); b = imerg.fetch_field(grid, ts[1])

def mae(x, y):
    m = np.isfinite(x) & np.isfinite(y) & (y > 5)
    return float(np.abs(x[m]-y[m]).mean()), int(m.sum())

for dx, dy in ((0,4),(0,-4),(4,0),(-4,0),(2,4)):
    u = np.full(a.shape, dx, np.float32); v = np.full(a.shape, dy, np.float32)
    print(dx, dy, mae(advect(a,u,v), b))
print("persist", mae(a,b))
