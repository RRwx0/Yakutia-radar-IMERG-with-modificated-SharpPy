import os, numpy as np
from PIL import Image
for p in ["data/tiles/obs_11/5/30/8.png", "data/tiles/obs_11/5/30/9.png", "data/tiles/obs_11/6/61/17.png"]:
    print(p, os.path.exists(p), os.path.getsize(p) if os.path.exists(p) else "-")
    if os.path.exists(p):
        a = np.asarray(Image.open(p).convert("RGBA"))
        print("  shape", a.shape, "colored", int((a[...,3]>10).sum()))

shot = np.asarray(Image.open("client/index-verify/1440.png").convert("RGB"))
h, w, _ = shot.shape
region = shot[100:760, 350:1250]
r, g, b = region[...,0].astype(int), region[...,1].astype(int), region[...,2].astype(int)
mx = np.maximum(np.maximum(r,g),b); mn = np.minimum(np.minimum(r,g),b)
sat = mx - mn
colored = (sat > 60) & (mx > 90)
print("screenshot colored px", int(colored.sum()), "of", region.shape[0]*region.shape[1])
