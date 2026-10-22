import sys
sys.path.insert(0, ".")
import numpy as np
from radar.grid import Grid
from radar.sources import imerg
from radar.nowcast import advect, skill

grid = Grid()
ts = imerg.frames(2)
a = imerg.fetch_field(grid, ts[0]); b = imerg.fetch_field(grid, ts[1])

def global_motion(a, b, scale=4):
    h, w = a.shape
    h2, w2 = h // scale * scale, w // scale * scale
    a0 = np.nan_to_num(a)[:h2, :w2].reshape(h2//scale, scale, w2//scale, scale).mean(axis=(1,3))
    b0 = np.nan_to_num(b)[:h2, :w2].reshape(h2//scale, scale, w2//scale, scale).mean(axis=(1,3))
    win = np.outer(np.hanning(a0.shape[0]), np.hanning(a0.shape[1]))
    A = np.fft.rfft2(a0 * win); B = np.fft.rfft2(b0 * win)
    R = A * np.conj(B); R /= np.abs(R) + 1e-9
    c = np.fft.irfft2(R, s=a0.shape)
    dy, dx = np.unravel_index(np.argmax(c), c.shape)
    if dy > a0.shape[0] // 2: dy -= a0.shape[0]
    if dx > a0.shape[1] // 2: dx -= a0.shape[1]
    return dx * scale, dy * scale

dx, dy = global_motion(a, b)
print("global shift px", dx, dy)
u = np.full(a.shape, dx, dtype=np.float32); v = np.full(a.shape, dy, dtype=np.float32)
print("skill const", skill(a, advect(a, u, v), b))
print("skill persist", skill(a, a, b))
