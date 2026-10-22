from __future__ import annotations

import numpy as np

STOPS = (
    (5.0, (164, 248, 241)),
    (10.0, (109, 184, 225)),
    (15.0, (63, 143, 210)),
    (20.0, (0, 131, 62)),
    (25.0, (0, 151, 31)),
    (30.0, (143, 214, 0)),
    (35.0, (253, 203, 0)),
    (40.0, (255, 152, 16)),
    (45.0, (255, 101, 25)),
    (50.0, (255, 45, 45)),
    (55.0, (206, 0, 0)),
    (60.0, (150, 0, 60)),
    (70.0, (212, 0, 160)),
)


def build_lut() -> np.ndarray:
    lut = np.zeros((256, 4), dtype=np.uint8)
    values = np.linspace(5.0, 70.0, 256)
    for i, value in enumerate(values):
        lo = STOPS[0]
        hi = STOPS[-1]
        for a, b in zip(STOPS[:-1], STOPS[1:]):
            if a[0] <= value <= b[0]:
                lo, hi = a, b
                break
        t = 0.0 if hi[0] == lo[0] else (value - lo[0]) / (hi[0] - lo[0])
        rgb = [int(round(lo[1][k] + (hi[1][k] - lo[1][k]) * t)) for k in range(3)]
        lut[i, :3] = rgb
        lut[i, 3] = 0 if value < 5.0 else 210
    lut[:2, 3] = 0
    return lut


LUT = build_lut()


def colorize(dbz: np.ndarray, alpha: int = 235) -> np.ndarray:
    idx = np.clip(((np.nan_to_num(dbz, nan=5.0) - 5.0) / 65.0 * 255).astype(np.int32), 0, 255)
    rgba = LUT[idx]
    out = rgba.copy()
    out[..., 3] = np.where(np.isfinite(dbz) & (dbz >= 5.0), alpha, 0).astype(np.uint8)
    return out
