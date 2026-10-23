from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .config import DATA
from .grid import Grid


def _load_env() -> dict | None:
    path = DATA / "env.npz"
    if not path.exists():
        return None
    with np.load(path) as z:
        return {
            "cape": np.asarray(z["cape"], np.float32),
            "shear": np.asarray(z["shear"], np.float32),
            "t2m": np.asarray(z["t2m"], np.float32),
        }


def _zones(env: dict) -> list[dict]:
    cape = env["cape"]
    shear = env["shear"]
    t2m = env["t2m"]
    grid = Grid()
    coarse = Grid(step=1.0)

    def agg(field: np.ndarray, lat: float, lon: float) -> float:
        iy = int(round((lat - grid.lat_min) / grid.step))
        ix = int(round((lon - grid.lon_min) / grid.step))
        iy = max(0, min(grid.ny - 1, iy))
        ix = max(0, min(grid.nx - 1, ix))
        return float(field[iy, ix])

    zones = []
    for iy in range(coarse.ny):
        lat0 = coarse.lat_min + iy * coarse.step
        for ix in range(coarse.nx):
            lon0 = coarse.lon_min + ix * coarse.step
            c = agg(cape, lat0, lon0)
            s = agg(shear, lat0, lon0)
            t = agg(t2m, lat0, lon0)
            if not (np.isfinite(c) and np.isfinite(s) and np.isfinite(t)):
                continue
            # холодный сезон: сильный сдвиг ветра => шквалы/метель, а не грозы
            if t < 5:
                if s >= 25:
                    zones.append(
                        {
                            "lat": round(lat0, 2),
                            "lon": round(lon0, 2),
                            "kind": "severe",
                            "label": "Предупреждение: сильный ветер/шквалы",
                            "color": "#ff2d55",
                            "cape": round(c),
                            "shear": round(s, 1),
                        }
                    )
                elif s >= 18:
                    zones.append(
                        {
                            "lat": round(lat0, 2),
                            "lon": round(lon0, 2),
                            "kind": "watch",
                            "label": "Наблюдение: порывистый ветер",
                            "color": "#ffb454",
                            "cape": round(c),
                            "shear": round(s, 1),
                        }
                    )
                continue
            # тёплый сезон: грозы по CAPE + сдвиг
            if c >= 1500 and s >= 15:
                kind, label, color = "severe", "Предупреждение: сильная гроза", "#ff2d55"
            elif c >= 800 and s >= 10:
                kind, label, color = "watch", "Наблюдение: возможны грозы", "#ffb454"
            elif c >= 300:
                kind, label, color = "mention", "Неустойчиво: отдельные грозы", "#ffd97a"
            else:
                continue
            zones.append(
                {
                    "lat": round(lat0, 2),
                    "lon": round(lon0, 2),
                    "kind": kind,
                    "label": label,
                    "color": color,
                    "cape": round(c),
                    "shear": round(s, 1),
                }
            )
    return zones


def _merge(zones: list[dict], step: float = 1.0) -> list[dict]:
    """Схлопывает соседние зоны в группы — меньше шума на карте."""
    if not zones:
        return []
    cells = {(z["lat"], z["lon"]): z for z in zones}
    merged: list[dict] = []
    used: set = set()
    for z in zones:
        if (z["lat"], z["lon"]) in used:
            continue
        used.add((z["lat"], z["lon"]))
        group = [z]
        stack = [(z["lat"], z["lon"])]
        while stack:
            la, lo = stack.pop()
            for dla in (-step, 0, step):
                for dlo in (-step, 0, step):
                    if dla == 0 and dlo == 0:
                        continue
                    k = (round(la + dla, 2), round(lo + dlo, 2))
                    if k in cells and k not in used:
                        used.add(k)
                        group.append(cells[k])
                        stack.append(k)
        if not group:
            continue
        worst = max(group, key=lambda g: (g["kind"] == "severe", g["kind"] == "watch", g["cape"]))
        lats = [g["lat"] for g in group]
        lons = [g["lon"] for g in group]
        merged.append(
            {
                "kind": worst["kind"],
                "label": worst["label"],
                "color": worst["color"],
                "lat": round(sum(lats) / len(lats), 2),
                "lon": round(sum(lons) / len(lons), 2),
                "bounds": [
                    [min(lats), min(lons)],
                    [max(lats), max(lons)],
                ],
                "cape": worst["cape"],
                "shear": worst["shear"],
                "count": len(group),
                "issued": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
            }
        )
    # топ-8 по серьёзности
    order = {"severe": 0, "watch": 1, "mention": 2}
    merged.sort(key=lambda m: (order[m["kind"]], -m["cape"]))
    return merged[:8]


def warnings() -> dict:
    env = _load_env()
    if env is None:
        return {"available": False, "zones": []}
    zones = _zones(env)
    merged = _merge(zones)
    return {
        "available": True,
        "source": "GFS · наш расчёт, не официальное предупреждение",
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "count": len(merged),
        "zones": merged,
    }