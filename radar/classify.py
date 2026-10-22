from __future__ import annotations

import numpy as np

from .phase import SNOW, MIXED

TYPE_META = {
    "thunder": {"label": "гроза", "color": "#ff2d55"},
    "shower": {"label": "ливень", "color": "#ff9810"},
    "rain": {"label": "дождь", "color": "#3f8fd2"},
    "snow": {"label": "снег", "color": "#a8dcff"},
    "mixed": {"label": "смешанные", "color": "#c9a8ff"},
}


def cell_features(
    field: np.ndarray,
    ys: np.ndarray,
    xs: np.ndarray,
    code: np.ndarray | None = None,
    cape: np.ndarray | None = None,
    shear: np.ndarray | None = None,
    km2: float = 5.3,
) -> dict:
    vals = field[ys, xs]
    peak = float(vals.max())
    bbox = (int(ys.max() - ys.min() + 1)) * (int(xs.max() - xs.min() + 1))
    gy, gx = np.gradient(field)
    cy, cx = int(ys.mean()), int(xs.mean())
    return {
        "peak_dbz": round(peak, 1),
        "mean_dbz": round(float(vals.mean()), 1),
        "area_km2": int(vals.size * km2),
        "core45_km2": int((vals >= 45).sum() * km2),
        "fill": round(float(vals.size / max(bbox, 1)), 2),
        "gradient": round(float(np.hypot(gy, gx)[ys, xs].mean()), 2),
        "phase": int(np.bincount(code[ys, xs]).argmax()) if code is not None else 3,
        "cape": round(float(cape[cy, cx]), 0) if cape is not None else 0.0,
        "shear": round(float(shear[cy, cx]), 1) if shear is not None else 0.0,
    }


def label_cell(f: dict, growth: float | None = None) -> dict:
    score = 0.0
    reasons: list[str] = []

    peak = f["peak_dbz"]
    if peak >= 50:
        score += 3
    elif peak >= 45:
        score += 2
    elif peak >= 40:
        score += 1
    reasons.append(f"пик {peak:.0f} дБЗ")

    core = f["core45_km2"]
    if core >= 50:
        score += 2
    elif core >= 10:
        score += 1
    if core:
        reasons.append(f"ядро ≥45: {core} км²")

    if f["fill"] >= 0.55:
        score += 1
    if f["gradient"] >= 3.0:
        score += 1
    cape = f.get("cape", 0) or 0
    if cape >= 1200:
        score += 2
    elif cape >= 700:
        score += 1
    if cape:
        reasons.append(f"CAPE {cape:.0f}")
    shear = f.get("shear", 0) or 0
    if shear >= 15:
        score += 1
    if shear:
        reasons.append(f"сдвиг {shear:.0f} м/с")
    if growth is not None and growth >= 5:
        score += 1
        reasons.append(f"рост +{growth:.0f} дБЗ")

    phase = f.get("phase", 3)
    if phase == SNOW:
        score -= 3
        reasons.append("фаза: снег")
    elif phase == MIXED:
        score -= 1
        reasons.append("фаза: смешанные")

    if phase == SNOW:
        kind = "snow"
        conf = min(1.0, max(0.0, (peak - 15) / 35))
    elif phase == MIXED and score < 4:
        kind = "mixed"
        conf = min(1.0, max(0.0, score / 8))
    elif score >= 6:
        kind = "thunder"
        conf = min(1.0, score / 8)
    elif score >= 4:
        kind = "shower"
        conf = min(1.0, score / 8)
    else:
        kind = "rain"
        conf = min(1.0, max(0.0, score / 6))

    return {
        "type": kind,
        "label": TYPE_META[kind]["label"],
        "color": TYPE_META[kind]["color"],
        "confidence": round(float(conf), 2),
        "score": round(float(score), 1),
        "reasons": reasons,
    }
