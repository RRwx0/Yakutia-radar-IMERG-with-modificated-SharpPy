from __future__ import annotations

import numpy as np

STOPS = (
    (5.0, (201, 242, 229)),
    (8.0, (159, 219, 224)),
    (12.0, (124, 196, 216)),
    (16.0, (93, 168, 198)),
    (20.0, (127, 201, 143)),
    (25.0, (143, 200, 116)),
    (30.0, (201, 214, 107)),
    (35.0, (232, 209, 90)),
    (40.0, (232, 168, 76)),
    (45.0, (224, 122, 82)),
    (50.0, (213, 96, 90)),
    (55.0, (180, 74, 109)),
    (60.0, (148, 80, 166)),
    (65.0, (111, 79, 158)),
    (70.0, (80, 62, 142)),
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
