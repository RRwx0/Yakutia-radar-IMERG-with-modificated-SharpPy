import glob, numpy as np
from PIL import Image
files = glob.glob("data/tiles/obs_11/4/*/*.png")
print("z4 files", len(files))
for f in files[:4]:
    a = np.asarray(Image.open(f).convert("RGBA"))
    colored = int((a[...,3] > 10).sum())
    print(f, a.shape, "colored px", colored)
files5 = glob.glob("data/tiles/obs_11/5/*/*.png")
best = sorted(files5, key=lambda p: -__import__("os").path.getsize(p))[:2]
for f in best:
    a = np.asarray(Image.open(f).convert("RGBA"))
    print("z5", f, "colored", int((a[...,3] > 10).sum()))
