import numpy as np, json
p = np.load("data/probe/obs_11.npy")  # float16 62x? 
print("shape", p.shape)
iy, ix = np.unravel_index(np.argmax(p), p.shape)
lat = 54 + iy * 0.1
lon = 104 + ix * 0.1
print("max dbz", float(p[iy, ix]), "lat", round(lat,2), "lon", round(lon,2))
