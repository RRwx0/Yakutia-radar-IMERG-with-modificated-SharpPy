from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MANIFEST = DATA / "manifest.json"
PROBE_DIR = DATA / "probe"
CLIENT = ROOT / "client"
TILES = CLIENT / "tiles"

app = FastAPI(title="IMERG Sakha — precipitation nowcasting", version="1.1")
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "HEAD", "OPTIONS"],
    allow_headers=["*"],
)

_cache: dict[str, np.ndarray] = {}


@app.middleware("http")
async def cache_headers(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/tiles/"):
        response.headers["Cache-Control"] = "public, max-age=86400, immutable"
    elif path.endswith((".js", ".css", ".png", ".svg", ".woff2")):
        response.headers["Cache-Control"] = "public, max-age=3600"
    return response


def manifest() -> dict:
    if not MANIFEST.exists():
        raise HTTPException(503, "manifest is not built; run python -m radar.pipeline")
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def probe_array(frame_id: str, kind: str = "") -> np.ndarray | None:
    path = PROBE_DIR / f"{frame_id}{kind}.npy"
    if not path.exists():
        return None
    key = path.name
    if key not in _cache:
        _cache[key] = np.load(path)
    return _cache[key]


def class_of(dbz: float) -> dict:
    table = (
        (10, "следы", "#a4f8f1"),
        (15, "слабые", "#6db8e1"),
        (20, "небольшие", "#3f8fd2"),
        (25, "умеренные", "#00833e"),
        (30, "умеренный дождь", "#00971f"),
        (35, "сильные", "#8fd600"),
        (40, "очень сильные", "#fdcb00"),
        (45, "ливневые", "#ff9810"),
        (50, "гроза/град", "#ff2d2d"),
        (1000, "экстремальные", "#ce0000"),
    )
    for limit, name, color in table:
        if dbz < limit:
            return {"name": name, "color": color}
    return {"name": "экстремальные", "color": "#ce0000"}


def nearest_station(lat: float, lon: float) -> dict:
    best = None
    for s in manifest()["stations"]:
        d = 2 * 6371 * math.asin(
            math.sqrt(
                math.sin(math.radians(lat - s["lat"]) / 2) ** 2
                + math.cos(math.radians(lat))
                * math.cos(math.radians(s["lat"]))
                * math.sin(math.radians(lon - s["lon"]) / 2) ** 2
            )
        )
        if best is None or d < best["distance_km"]:
            best = {"name": s["name"], "id": s["id"], "distance_km": round(d, 1), "range_km": s["range_km"]}
    return best or {}


def probe_index(lat: float, lon: float) -> tuple[int, int] | None:
    step = manifest()["probe"]["step"]
    lat0 = manifest()["region"]["bounds"][0][0]
    lon0 = manifest()["region"]["bounds"][0][1]
    iy = int(round((lat - lat0) / step))
    ix = int(round((lon - lon0) / step))
    arr = probe_array("obs_00")
    if arr is None:
        return None
    if 0 <= iy < arr.shape[0] and 0 <= ix < arr.shape[1]:
        return iy, ix
    return None


@app.get("/api/health")
def health():
    m = manifest()
    return {"ok": True, "frames": len(m["frames"]), "generated_at": m["generated_at"]}


@app.get("/api/state")
def state(request: Request):
    m = manifest()
    etag = '"' + str(abs(hash(m["generated_at"]))) + '"'
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers={"ETag": etag})
    return JSONResponse(m, headers={"ETag": etag, "Cache-Control": "no-cache"})


@app.get("/api/probe")
def probe(
    lat: float = Query(..., ge=40, le=85),
    lon: float = Query(..., ge=-180, le=180),
    frame: str | None = None,
):
    m = manifest()
    ids = [f["id"] for f in m["frames"]]
    frame_id = frame if frame in ids else next((f["id"] for f in reversed(m["frames"]) if f["kind"] == "obs"), ids[-1])
    info = next(f for f in m["frames"] if f["id"] == frame_id)

    idx = probe_index(lat, lon)
    arr = probe_array(frame_id)
    if idx is None or arr is None:
        return {"frame": frame_id, "dbz": None, "error": "outside probe grid"}

    value = float(arr[idx])
    dbz = None if value <= -90 else round(value, 1)
    prob = None
    if info["kind"] == "nowcast":
        prob_arr = probe_array(frame_id, "_prob")
        if prob_arr is not None:
            prob = round(float(prob_arr[idx]), 2)

    trend = None
    obs = [f["id"] for f in m["frames"] if f["kind"] == "obs"]
    if frame_id in obs and len(obs) > 3:
        pos = obs.index(frame_id)
        prev = probe_array(obs[max(0, pos - 3)])
        if prev is not None:
            pv = float(prev[idx])
            if pv > -90 and dbz is not None:
                trend = round(dbz - pv, 1)

    station = nearest_station(lat, lon)
    return {
        "frame": frame_id,
        "time": info["time"],
        "kind": info["kind"],
        "lead_min": info["lead_min"],
        "dbz": dbz,
        "class": class_of(dbz) if dbz is not None else None,
        "prob30": prob,
        "trend_30m_dbz": trend,
        "nearest": station,
        "in_range": bool(station and station.get("distance_km", 999) <= station.get("range_km", 0)),
    }


@app.get("/api/archive")
def api_archive(date: str = Query(..., min_length=10, max_length=10), hour: int = Query(12, ge=0, le=23)):
    if date < "2025-01-01":
        raise HTTPException(400, "archive starts 2025-01-01")
    today = np.datetime64("today").astype(str)
    if date > today:
        raise HTTPException(400, "date is in the future")
    from server import archive as archive_mod

    return archive_mod.request(date, hour)


@app.get("/api/archive/status")
def api_archive_status(key: str):
    from server import archive as archive_mod

    return archive_mod.status(key)


@app.get("/api/accum")
def api_accum(lat: float, lon: float, frame: str | None = None, window: int = Query(12, ge=1, le=48)):
    m = manifest()
    ids = [f["id"] for f in m["frames"]]
    frame_id = frame if frame in ids else ids[-1]
    idx = ids.index(frame_id)
    idxs = probe_index(lat, lon)
    if idxs is None:
        return {"mm": None, "frames": 0}
    total = 0.0
    used = 0
    for fid in ids[max(0, idx - window + 1) : idx + 1]:
        arr = probe_array(fid)
        if arr is None:
            continue
        value = float(arr[idxs])
        if value <= -90:
            continue
        rate = (10 ** (value / 10.0) / 200.0) ** (1 / 1.6)
        total += rate * 0.5
        used += 1
    return {"mm": round(total, 1), "frames": used, "hours": round(used * 0.5, 1), "frame": frame_id}


app.mount("/tiles", StaticFiles(directory=str(TILES)), name="tiles")


@app.get("/api/models")
def models_list():
    from radar.sources import models

    return {
        k: {"name": v[0], "status": v[1], "url": v[2]}
        for k, v in models.describe().items()
    }


@app.get("/api/model_field")
def model_field(model: str = "gfs"):
    from radar.grid import Grid
    from radar.sources import models

    env = models.fetch(Grid(), model)
    if env is None:
        raise HTTPException(503, f"модель «{model}» сейчас недоступна")
    field = env["field"]
    finite = np.isfinite(field)
    payload = {
        "model": model,
        "name": env["name"],
        "init": env.get("valid") or env.get("init"),
        "bounds": [[54.0, 104.0], [74.0, 166.0]],
        "level": "surface",
        "field": [round(float(v), 1) if np.isfinite(v) else None for v in field.ravel()],
        "ny": int(field.shape[0]),
        "nx": int(field.shape[1]),
        "max_dbz": round(float(np.nanmax(field)), 1) if finite.any() else None,
        "note": env.get("note"),
    }
    return payload


@app.get("/api/sounding/stations")
def sounding_stations(q: str = ""):
    from server import sounding as snd

    items = [
        {"wmo": k, "name": v[0], "lat": v[1], "lon": v[2]}
        for k, v in snd.STATIONS.items()
    ]
    if q:
        ql = q.lower()
        items = [i for i in items if ql in i["name"].lower() or q in i["wmo"]]
    return items


@app.get("/api/sounding/times")
def sounding_times(station: str, year: int = 0):
    from server import sounding as snd

    try:
        return {"times": snd.times(station, year or None)}
    except Exception as e:
        raise HTTPException(502, f"архив станции недоступен: {e}")


@app.get("/api/sounding/profile")
def sounding_profile(station: str, time: str):
    from server import sounding as snd

    try:
        prof = snd.profile(station, time)
    except Exception as e:
        raise HTTPException(502, f"не удалось прочитать архив: {e}")
    if not prof:
        raise HTTPException(404, "нет такого срока")
    return prof


@app.get("/api/sounding/snd")
def sounding_snd(station: str, time: str):
    from fastapi.responses import PlainTextResponse

    from server import sounding as snd

    prof = snd.profile(station, time)
    if not prof:
        raise HTTPException(404, "нет такого срока")
    return PlainTextResponse(
        snd.to_snd(prof),
        headers={"Content-Disposition": f'attachment; filename="{station}_{time[:10]}.snd"'},
    )


app.mount("/", StaticFiles(directory=str(CLIENT), html=True), name="client")
