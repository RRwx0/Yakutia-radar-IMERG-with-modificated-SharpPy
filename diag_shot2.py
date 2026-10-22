import numpy as np
from PIL import Image
shot = np.asarray(Image.open("client/index-verify/1440.png").convert("RGB"))
region = shot[100:760, 350:1250]
r, g, b = region[...,0].astype(int), region[...,1].astype(int), region[...,2].astype(int)
mx = np.maximum(np.maximum(r,g),b); mn = np.minimum(np.minimum(r,g),b)
colored = ((mx - mn) > 60) & (mx > 90)
print("colored px", int(colored.sum()))
