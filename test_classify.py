from __future__ import annotations

import numpy as np

from radar.cells import detect_cells


def blob(peak: float, sigma: float, n: int = 70) -> np.ndarray:
    yy, xx = np.mgrid[0:n, 0:n]
    c = n // 2
    r2 = (yy - c) ** 2 + (xx - c) ** 2
    return (peak * np.exp(-r2 / (2 * sigma**2))).astype(np.float32)


def run(field, phase=3, cape=0.0, shear=0.0):
    lats = np.linspace(70, 54, field.shape[0])
    lons = np.linspace(104, 166, field.shape[1])
    code = np.full(field.shape, phase, dtype=np.int8)
    cape_g = np.full(field.shape, cape, dtype=np.float32)
    shear_g = np.full(field.shape, shear, dtype=np.float32)
    cells = detect_cells(field, lats, lons, code=code, cape=cape_g, shear=shear_g)
    return cells[0] if cells else None


def main():
    thunder = run(blob(58, 3.0), phase=3, cape=1500, shear=20)
    assert thunder and thunder["type"] == "thunder", thunder
    print("thunder:", thunder["label"], thunder["confidence"], thunder["reasons"])

    weak = run(blob(37, 7.0), phase=3, cape=100, shear=4)
    assert weak and weak["type"] in ("rain", "shower"), weak
    assert weak["type"] != "thunder"
    print("weak:", weak["label"], weak["confidence"], weak["reasons"])

    snow = run(blob(36, 6.0), phase=1, cape=0, shear=3)
    assert snow and snow["type"] == "snow", snow
    print("snow:", snow["label"], snow["confidence"], snow["reasons"])

    mixed = run(blob(38, 6.0), phase=2, cape=300, shear=6)
    assert mixed and mixed["type"] == "mixed", mixed
    print("mixed:", mixed["label"], mixed["confidence"])
    print("OK")


if __name__ == "__main__":
    main()
