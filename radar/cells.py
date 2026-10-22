from __future__ import annotations

import numpy as np
from scipy import ndimage

from .classify import cell_features, label_cell

CELL_AREA_KM2 = 5.3


def detect_cells(
    field: np.ndarray,
    lats: np.ndarray,
    lons: np.ndarray,
    threshold: float = 35.0,
    top: int = 5,
    code: np.ndarray | None = None,
    cape: np.ndarray | None = None,
    shear: np.ndarray | None = None,
) -> list[dict]:
    mask = np.isfinite(field) & (field >= threshold)
    if not mask.any():
        return []
    labels, count = ndimage.label(mask)
    if count == 0:
        return []
    cells = []
    for idx in range(1, count + 1):
        ys, xs = np.where(labels == idx)
        if ys.size < 8:
            continue
        values = field[ys, xs]
        peak = float(values.max())
        area = float(ys.size * CELL_AREA_KM2)
        cy, cx = int(ys.mean()), int(xs.mean())
        features = cell_features(field, ys, xs, code=code, cape=cape, shear=shear)
        tags = label_cell(features)
        cells.append(
            {
                "lat": round(float(lats[cy]), 2),
                "lon": round(float(lons[cx]), 2),
                "max_dbz": round(peak, 1),
                "area_km2": int(area),
                "pixels": int(ys.size),
                "type": tags["type"],
                "label": tags["label"],
                "color": tags["color"],
                "confidence": tags["confidence"],
                "score": tags["score"],
                "reasons": tags["reasons"],
                "features": features,
            }
        )
    cells.sort(key=lambda c: (c["type"] == "thunder", c["score"], c["max_dbz"]), reverse=True)
    return cells[:top]


def cell_growth(prev: list[dict], curr: list[dict], max_km: float = 60.0) -> list[dict]:
    used: set[int] = set()
    out = []
    for c in curr:
        best = None
        best_d = max_km
        for i, p in enumerate(prev):
            if i in used:
                continue
            d = np.hypot((c["lat"] - p["lat"]) * 111.0, (c["lon"] - p["lon"]) * 111.0 * np.cos(np.radians(c["lat"])))
            if d < best_d:
                best_d = d
                best = i
        growth = None
        if best is not None:
            used.add(best)
            growth = round(c["max_dbz"] - prev[best]["max_dbz"], 1)
        item = dict(c)
        item["growth_dbz"] = growth
        tags = label_cell(c["features"], growth)
        item.update(
            {
                "type": tags["type"],
                "label": tags["label"],
                "color": tags["color"],
                "confidence": tags["confidence"],
                "score": tags["score"],
                "reasons": tags["reasons"],
            }
        )
        out.append(item)
    return out
