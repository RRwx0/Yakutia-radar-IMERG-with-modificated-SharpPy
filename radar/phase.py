from __future__ import annotations

import numpy as np


def wet_bulb(t2m: np.ndarray, rh: np.ndarray) -> np.ndarray:
    """Stull (2011) wet-bulb from 2 m temperature (°C) and relative humidity (%)."""
    t = np.asarray(t2m, dtype=np.float32)
    h = np.clip(np.asarray(rh, dtype=np.float32), 5.0, 99.0)
    tw = (
        t * np.arctan(0.151977 * np.sqrt(h + 8.313659))
        + np.arctan(t + h)
        - np.arctan(h - 1.676331)
        + 0.00391838 * np.power(h, 1.5) * np.arctan(0.023101 * h)
        - 4.686035
    )
    return tw.astype(np.float32)


SNOW, MIXED, RAIN = 1, 2, 3


def classify(t2m: np.ndarray, rh: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Phase codes: 1 snow, 2 mixed, 3 rain; second array is wet-bulb temperature."""
    tw = wet_bulb(t2m, rh)
    code = np.full(tw.shape, RAIN, dtype=np.int8)
    code[tw <= 0.5] = SNOW
    code[(tw > 0.5) & (tw < 2.0)] = MIXED
    return code, tw


def phase_name(code: int) -> str:
    return {SNOW: "снег", MIXED: "смешанные", RAIN: "дождь"}.get(int(code), "—")


def _rate_from_dbz(dbz: np.ndarray) -> np.ndarray:
    return np.power(np.power(10.0, dbz / 10.0) / 200.0, 1.0 / 1.6)


def adjust_dbz(dbz: np.ndarray, code: np.ndarray, tw: np.ndarray) -> np.ndarray:
    """Phase-aware Z–R: rain Z=200R^1.6, snow Z=2000R^2, mixed blended in Z by wet-bulb."""
    rain_z = np.power(10.0, dbz / 10.0)
    rate = _rate_from_dbz(dbz)
    snow_z = 2000.0 * np.square(rate)
    w = np.clip((tw - 0.5) / 1.5, 0.0, 1.0)
    z = np.where(code == SNOW, snow_z, np.where(code == MIXED, w * rain_z + (1.0 - w) * snow_z, rain_z))
    out = 10.0 * np.log10(np.maximum(z, 1e-3))
    return np.where(np.isfinite(dbz), out, np.nan).astype(np.float32)


def rate_of(dbz: float, code: int = RAIN) -> float:
    if not np.isfinite(dbz):
        return float("nan")
    z = 10.0 ** (dbz / 10.0)
    if code == SNOW:
        return float(np.sqrt(z / 2000.0))
    if code == MIXED:
        return float(np.sqrt(z / 2000.0))
    return float(np.power(z / 200.0, 1.0 / 1.6))
