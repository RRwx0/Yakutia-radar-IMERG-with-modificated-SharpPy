import sys
sys.path.insert(0, ".")
import numpy as np
from radar.grid import Grid
from radar.sources import imerg
from radar.nowcast import advect

grid = Grid()
ts = imerg.frames(2)
a = np.nan_to_num(imerg.fetch_field(grid, ts[0]), nan=0.0)
b = np.nan_to_num(imerg.fetch_field(grid, ts[1]), nan=0.0)

def mae(x, y):
    m = (y > 5)
    return float(np.abs(x[m]-y[m]).mean()), int(m.sum())

print("persist", mae(a,b))
for dx, dy in ((0,4),(0,-4),(4,0),(-4,0),(2,4),(-2,-4)):
    u = np.full(a.shape, dx, np.float32); v = np.full(a.shape, dy, np.float32)
    print(dx, dy, mae(advect(a,u,v), b))
