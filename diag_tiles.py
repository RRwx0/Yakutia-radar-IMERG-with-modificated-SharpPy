import glob, os, numpy as np, json
from PIL import Image
m = json.load(open("data/manifest.json", encoding="utf-8"))
print("zoom tiles", m["frames"][11]["zoom_tiles"])
for z in (3, 4, 5):
    files = glob.glob(f"data/tiles/obs_11/{z}/*/*.png")
    total = 0
    per = []
    for f in files:
        a = np.asarray(Image.open(f).convert("RGBA"))
        c = int((a[..., 3] > 10).sum())
        total += c
        per.append((c, os.path.basename(os.path.dirname(f)) + "/" + os.path.basename(f)))
    per.sort(reverse=True)
    print("z", z, "files", len(files), "colored", total, "top", per[:3])
