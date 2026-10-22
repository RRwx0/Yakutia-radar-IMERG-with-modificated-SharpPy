from pathlib import Path

p = Path("radar/sources/models.py")
s = p.read_text(encoding="utf-8")

old_caller = '''def fetch(grid: Grid, key: str) -> dict | None:
    if key == "gfs":
        return fetch_gfs(grid)
    return fetch_openmeteo(grid, key)'''

new_caller = '''def fetch(grid: Grid, key: str) -> dict | None:
    if key == "gfs":
        return fetch_gfs(grid)
    return fetch_openmeteo(grid, key)


def available() -> dict[str, dict]:
    """Статус моделей: gfs — прямой источник; остальные — через Open-Meteo."""
    import requests as _rq

    out = {k: {"name": v[0], "source": v[1], "ok": False, "reason": ""} for k, v in MODELS.items()}
    # gfs: проверим, отвечает ли NOMADS
    try:
        r = _rq.get(
            "https://nomads.ncep.noaa.gov/",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
        )
        out["gfs"]["ok"] = r.status_code == 200
        out["gfs"]["reason"] = "" if r.status_code == 200 else f"HTTP {r.status_code}"
    except Exception as e:
        out["gfs"]["ok"] = False
        out["gfs"]["reason"] = type(e).__name__
    # open-meteo: пробуем точкой
    for key in ("ecmwf", "icon", "msm"):
        try:
            r = _rq.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": 62.0,
                    "longitude": 129.7,
                    "hourly": "precipitation",
                    "models": OPENMETEO_KEYS[key],
                    "forecast_days": 1,
                    "timezone": "UTC",
                },
                timeout=15,
            )
            out[key]["ok"] = r.status_code == 200
            out[key]["reason"] = "" if r.status_code == 200 else f"HTTP {r.status_code}"
        except Exception as e:
            out[key]["ok"] = False
            out[key]["reason"] = type(e).__name__
    return out'''

if old_caller in s:
    s = s.replace(old_caller, new_caller)
    p.write_text(s, encoding="utf-8")
    print("available() added")
else:
    print("caller NOT found")