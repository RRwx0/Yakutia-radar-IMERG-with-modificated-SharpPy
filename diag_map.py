import numpy as np
from PIL import Image
shot = np.asarray(Image.open("client/index-verify/1440.png").convert("RGB"))
region = shot[110:600, 340:980]
r, g, b = region[...,0].astype(int), region[...,1].astype(int), region[...,2].astype(int)
mx = np.maximum(np.maximum(r,g),b); mn = np.minimum(np.minimum(r,g),b)
colored = ((mx - mn) > 55) & (mx > 80)
print("map colored px", int(colored.sum()))
Image.fromarray(shot[100:640, 330:1000]).save("map-crop.png")
print("saved")
