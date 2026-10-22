from __future__ import annotations

import numpy as np
from scipy import ndimage


def clean_ppi(dbz: np.ndarray, rng_km: np.ndarray) -> tuple[np.ndarray, dict]:
    raw = dbz.astype(np.float32).copy()
    missing = ~np.isfinite(raw)

    near = rng_km[None, :] < 16.0
    high = raw > 32.0
    grad_r = np.abs(np.diff(raw, axis=1, prepend=raw[:, :1]))
    grad_a = np.abs(np.diff(raw, axis=0, prepend=raw[:1, :]))
    isolated = (grad_r > 22.0) | (grad_a > 22.0)
    clutter = near & high & isolated
    raw[clutter] = np.nan

    filled = raw.copy()
    n_az, n_r = filled.shape
    for j in range(n_r):
        col = filled[:, j]
        good = np.isfinite(col)
        if good.sum() >= 8:
            idx = np.arange(n_az)
            filled[:, j] = np.interp(idx, idx[good], col[good], period=n_az)
        elif good.sum() == 0:
            filled[:, j] = np.nan

    smooth = ndimage.median_filter(filled, size=(3, 3), mode="wrap")
    filled = np.where(np.isfinite(filled), smooth, np.nan)
    filled = np.where(filled < 2.0, np.nan, filled)

    stats = {
        "removed_clutter_pct": float(100.0 * clutter.sum() / max(1, clutter.size)),
        "missing_pct": float(100.0 * missing.mean()),
        "valid_pct": float(100.0 * np.isfinite(filled).mean()),
    }
    return filled.astype(np.float32), stats
