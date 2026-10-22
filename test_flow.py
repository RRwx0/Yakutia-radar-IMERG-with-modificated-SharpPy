import sys, numpy as np
sys.path.insert(0, ".")
from scipy.ndimage import gaussian_filter, shift
from radar.nowcast import estimate_flow

h, w = 300, 600
y, x = np.mgrid[0:h, 0:w]
f = 50*np.exp(-(((y-150)/22)**2 + ((x-250)/35)**2)) + 40*np.exp(-(((y-190)/16)**2 + ((x-380)/20)**2))
f = gaussian_filter(f, 1.0)
for du, dv in ((3,0),(1.6,0.4),(0,2.5)):
    g = shift(f, (dv, du), order=1)
    u, v = estimate_flow(f, g)
    print(f"true {du},{dv} -> est {u.mean():.2f},{v.mean():.2f}  center {u[150,250]:.2f},{v[150,250]:.2f}")
