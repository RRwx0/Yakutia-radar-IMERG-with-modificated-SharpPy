from __future__ import annotations


def severe_index(cells: list[dict], cape: float, shear: float) -> dict:
    peak = max((c["max_dbz"] for c in cells), default=0.0)
    area = max((c["area_km2"] for c in cells), default=0)
    growth = max((c.get("growth_dbz") or 0.0 for c in cells), default=0.0)

    score = 0
    score += 2 if peak >= 55 else (1 if peak >= 50 else 0)
    score += 1 if area >= 100 else 0
    score += 1 if area >= 500 else 0
    score += 1 if cape >= 1000 else (0.5 if cape >= 500 else 0)
    score += 1 if shear >= 15 else (0.5 if shear >= 8 else 0)
    score += 1 if growth >= 5 else 0

    level = "высокий" if score >= 5 else ("средний" if score >= 3 else "низкий")
    return {
        "score": round(float(score), 1),
        "level": level,
        "peak_dbz": peak,
        "area_km2": area,
        "growth_dbz": growth,
        "cape": None if cape is None else round(float(cape), 0),
        "shear": None if shear is None else round(float(shear), 1),
        "note": "индекс опасной грозы — прокси по отражаемости, площади, росту, CAPE и сдвигу",
    }
