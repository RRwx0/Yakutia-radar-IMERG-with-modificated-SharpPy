from __future__ import annotations

import numpy as np

from radar import phase, severe
from radar.cells import detect_cells


def blob(peak: float, sigma: float, n: int = 70) -> np.ndarray:
    yy, xx = np.mgrid[0:n, 0:n]
    c = n // 2
    r2 = (yy - c) ** 2 + (xx - c) ** 2
    return (peak * np.exp(-r2 / (2 * sigma**2))).astype(np.float32)


def main():
    t2m = np.array([[-20.0, -2.0, 5.0]])
    rh = np.array([[80.0, 80.0, 80.0]])
    code, tw = phase.classify(t2m, rh)
    assert code[0, 0] == phase.SNOW
    assert code[0, 2] == phase.RAIN

    rain = 30.0
    snow = phase.adjust_dbz(
        np.array([[rain]], dtype=np.float32),
        np.array([[phase.SNOW]], dtype=np.int8),
        np.array([[-5.0]], dtype=np.float32),
    )
    rain_dbz = phase.adjust_dbz(
        np.array([[rain]], dtype=np.float32),
        np.array([[phase.RAIN]], dtype=np.int8),
        np.array([[5.0]], dtype=np.float32),
    )
    assert float(snow[0, 0]) > float(rain_dbz[0, 0])

    lats = np.linspace(70, 54, 70)
    lons = np.linspace(104, 166, 70)
    field = blob(58, 3.0)
    cape = np.full(field.shape, 1500.0, dtype=np.float32)
    shear = np.full(field.shape, 20.0, dtype=np.float32)
    cells = detect_cells(field, lats, lons, code=np.full(field.shape, 3, dtype=np.int8), cape=cape, shear=shear)
    assert cells and cells[0]["type"] == "thunder", cells[:1]
    idx = severe.severe_index(cells, 1500.0, 20.0)
    assert idx["score"] >= 5, idx
    assert "cold_ring" not in idx
    print("severe:", idx["score"], idx["level"])
    print("OK")


if __name__ == "__main__":
    main()
