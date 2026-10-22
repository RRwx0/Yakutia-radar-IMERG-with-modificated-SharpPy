from __future__ import annotations

import math
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import requests
from metpy import calc as mpcalc
from metpy.units import units

DATA = Path(__file__).resolve().parents[1] / "data"
IGRA_DIR = DATA / "igra"
IGRA_BASE = "https://www.ncei.noaa.gov/pub/data/igra/data/data-por"
START = datetime(2011, 1, 1, tzinfo=timezone.utc)

STATIONS = {
    "24959": ("Якутск", 62.02, 129.72),
    "24266": ("Верхоянск", 67.55, 133.38),
    "24688": ("Оймякон", 63.25, 143.15),
    "24908": ("Вилюйск", 63.77, 121.62),
    "30710": ("Олёкминск", 60.40, 120.42),
    "24944": ("Хандыга", 62.67, 135.60),
    "21432": ("Тикси", 71.58, 128.92),
    "25123": ("Черский", 68.75, 161.28),
    "30758": ("Чита", 52.08, 113.48),
    "30635": ("Иркутск", 52.27, 104.35),
    "29634": ("Новосибирск", 55.03, 82.90),
    "29862": ("Красноярск", 56.18, 92.62),
    "31510": ("Благовещенск", 50.27, 127.50),
    "31960": ("Владивосток", 43.12, 131.93),
    "31736": ("Хабаровск", 48.53, 135.17),
    "32540": ("Петропавловск-Камчатский", 53.08, 158.58),
    "27612": ("Москва (Долгопрудный)", 55.75, 37.57),
    "26063": ("Санкт-Петербург", 59.97, 30.30),
    "34880": ("Астрахань", 46.28, 48.03),
}

_index_cache: dict[str, list[tuple[datetime, int, int]]] = {}
_profile_cache: dict[str, dict] = {}


def igra_id(wmo: str) -> str:
    return f"RSM000{wmo.zfill(5)}"


def _zip_path(wmo: str) -> Path:
    IGRA_DIR.mkdir(parents=True, exist_ok=True)
    return IGRA_DIR / f"{igra_id(wmo)}.zip"


def ensure_archive(wmo: str) -> Path:
    path = _zip_path(wmo)
    if path.exists() and path.stat().st_size > 1_000_000:
        return path
    url = f"{IGRA_BASE}/{igra_id(wmo)}-data.txt.zip"
    with requests.get(url, stream=True, timeout=300, headers={"User-Agent": "Mozilla/5.0"}) as r:
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    return path


def _index(wmo: str) -> list[tuple[datetime, int, int]]:
    if wmo in _index_cache:
        return _index_cache[wmo]
    path = ensure_archive(wmo)
    with zipfile.ZipFile(path) as z:
        raw = z.read(z.namelist()[0]).decode("utf-8", "replace")
    lines = raw.splitlines()
    out: list[tuple[datetime, int, int]] = []
    hdr = re.compile(r"^#\S+\s+(\d{4})\s+(\d{2})\s+(\d{2})\s+(\d{2})")
    for i, line in enumerate(lines):
        m = hdr.match(line)
        if not m:
            continue
        y, mo, d, h = (int(x) for x in m.groups())
        try:
            dt = datetime(y, mo, d, h, tzinfo=timezone.utc)
        except ValueError:
            continue
        if dt < START:
            continue
        try:
            nlev = int(line[32:36])
        except ValueError:
            nlev = 0
        out.append((dt, i, nlev))
    out.sort()
    _index_cache[wmo] = out
    return out


def times(wmo: str, year: int | None = None) -> list[str]:
    items = _index(wmo)
    if year:
        items = [x for x in items if x[0].year == year]
    return [x[0].strftime("%Y-%m-%dT%H:%MZ") for x in items]


def _val(s: str) -> float | None:
    s = s.strip()
    if not s:
        return None
    while s and not (s[-1].isdigit() or s[-1] in "-."):
        s = s[:-1]
    try:
        v = float(s)
    except ValueError:
        return None
    return None if v <= -9998 else v


def _parse_levels(lines: list[str], start: int, nlev: int) -> list[dict]:
    out = []
    for line in lines[start + 1:start + 1 + max(nlev, 60)]:
        if not line or line.startswith("#"):
            break
        p = _val(line[9:15])
        z = _val(line[16:21])
        t = _val(line[22:27])
        if p is None or t is None:
            continue
        p /= 100.0
        if not 100 <= p <= 1060:
            continue
        tv = t / 10.0

        # DPDP in IGRA is the dew-point depression (tenths of °C), not Td.
        dep = _val(line[34:39])
        wd = _val(line[40:45])
        wsp = _val(line[46:51])
        td = None if dep is None or not 0 <= dep <= 1000 else tv - dep / 10.0
        if td is not None and td > tv:
            td = tv
        out.append(
            {
                "p": p,
                "z": None if z is None else z,
                "t": tv,
                "td": td,
                "wd": wd,
                "ws": None if wsp is None else wsp / 10.0,
            }
        )
    out.sort(key=lambda r: -r["p"])
    merged: list[dict] = []
    for r in out:
        if merged and abs(merged[-1]["p"] - r["p"]) < 0.05:
            continue
        merged.append(r)
    return _fill_heights(merged)


def _fill_heights(levels: list[dict]) -> list[dict]:
    anchor = next((i for i, r in enumerate(levels) if r["z"] is not None), None)
    if anchor is None:
        for r in levels:
            r["z"] = 0.0
        return levels
    z = float(levels[anchor]["z"])
    for i in range(anchor + 1, len(levels)):
        tm = (levels[i - 1]["t"] + levels[i]["t"]) / 2 + 273.15
        z += 29.27 * tm * math.log(levels[i - 1]["p"] / levels[i]["p"])
        levels[i]["z"] = round(z, 1)
    z = float(levels[anchor]["z"])
    for i in range(anchor - 1, -1, -1):
        tm = (levels[i]["t"] + levels[i + 1]["t"]) / 2 + 273.15
        z -= 29.27 * tm * math.log(levels[i]["p"] / levels[i + 1]["p"])
        levels[i]["z"] = round(z, 1)
    return levels


def profile(wmo: str, iso: str) -> dict | None:
    key = f"{wmo}:{iso}"
    if key in _profile_cache:
        return _profile_cache[key]
    dt = datetime.strptime(iso, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
    hit = next((x for x in _index(wmo) if x[0] == dt), None)
    if not hit:
        return None
    path = _zip_path(wmo)
    with zipfile.ZipFile(path) as z:
        raw = z.read(z.namelist()[0]).decode("utf-8", "replace")
    levels = _parse_levels(raw.splitlines(), hit[1], hit[2])
    if len(levels) < 5:
        return None
    name, lat, lon = STATIONS.get(wmo, (wmo, None, None))
    res = {
        "station": wmo,
        "name": name,
        "lat": lat,
        "lon": lon,
        "time": iso,
        "source": "Росгидромет · IGRA",
        "levels": levels,
        "indices": indices(levels),
    }
    _profile_cache[key] = res
    return res


def _num(x, unit=None, digits=1):
    try:
        if hasattr(x, "to"):
            q = x.to(unit) if unit else x
            v = float(q.magnitude)
        else:
            v = float(x)
    except Exception:
        return None
    if not np.isfinite(v):
        return None
    return round(v, digits)


def indices(levels: list[dict]) -> dict:
    p = np.array([r["p"] for r in levels], float)
    z = np.array([r["z"] for r in levels], float)
    t = np.array([r["t"] for r in levels], float)
    td = np.array([r["td"] if r["td"] is not None else np.nan for r in levels], float)
    ws = np.array([r["ws"] if r["ws"] is not None else np.nan for r in levels], float)
    wd = np.array([r["wd"] if r["wd"] is not None else np.nan for r in levels], float)

    have_wind = np.isfinite(ws) & np.isfinite(wd)
    if have_wind.sum() >= 2:
        ws = np.interp(np.arange(len(ws)), np.where(have_wind)[0], ws[have_wind])
        wd = np.interp(np.arange(len(wd)), np.where(have_wind)[0], wd[have_wind])
        u = (-ws * np.sin(np.radians(wd))) * units("m/s")
        v = (-ws * np.cos(np.radians(wd))) * units("m/s")
    else:
        u = v = None

    have_td = np.isfinite(td)
    if have_td.sum() >= 2:
        td = np.interp(np.arange(len(td)), np.where(have_td)[0], td[have_td])
        td = np.minimum(td, t - 0.1)
    else:
        td = None

    P = p * units.hPa
    T = t * units.degC
    Z = z * units.m

    shear06 = srh03 = None
    motion = None
    if u is not None:
        try:
            su, sv = mpcalc.bulk_shear(P, u, v, height=Z, depth=6000 * units.m)
            shear06 = _num(np.hypot(su.magnitude, sv.magnitude), digits=1)
            rm, lm, mean = mpcalc.bunkers_storm_motion(P, u, v, Z)
            motion = {"u": _num(rm[0], digits=1), "v": _num(rm[1], digits=1)}
            _, _, srh = mpcalc.storm_relative_helicity(
                Z, u, v, depth=3000 * units.m, storm_u=rm[0], storm_v=rm[1]
            )
            srh03 = _num(srh, digits=0)
        except Exception:
            pass

    out = {
        "cape": None, "cin": None, "lcl": None, "lfc": None, "el": None,
        "li": None, "pw": None, "shear06": shear06, "srh03": srh03,
        "parcel": None, "storm_motion": motion,
    }
    if td is None:
        out["note"] = "в этом зондировании нет данных влажности"
        return out

    TD = td * units.degC
    try:
        p_mu, t_mu, td_mu, _ = mpcalc.most_unstable_parcel(P, T, TD, depth=300 * units.hPa)
        prof = mpcalc.parcel_profile(P, t_mu, td_mu)
        cape, cin = mpcalc.cape_cin(P, T, TD, prof)
        out["cape"] = _num(cape, digits=0)
        out["cin"] = _num(cin, digits=0)
        lcl_p, _lcl_t = mpcalc.lcl(p_mu, t_mu, td_mu)
        out["lcl"] = _num(lcl_p.to("hPa"))
        try:
            out["lfc"] = _num(mpcalc.lfc(P, T, TD, prof)[0].to("hPa"))
        except Exception:
            pass
        try:
            out["el"] = _num(mpcalc.el(P, T, TD, prof)[0].to("hPa"))
        except Exception:
            pass
        try:
            li = mpcalc.lifted_index(P, T, prof)
            out["li"] = _num(li[np.argmin(np.abs(p - 500))], digits=1)
        except Exception:
            pass
        out["pw"] = _num(mpcalc.precipitable_water(P, TD).to("mm"), digits=1)
        out["parcel"] = {"p": _num(p_mu, "hPa", 0), "t": _num(t_mu, "degC", 1), "td": _num(td_mu, "degC", 1)}
    except Exception as e:
        out["note"] = f"расчёт индексов не удался: {type(e).__name__}"
    return out


def to_snd(prof: dict) -> str:
    dt = datetime.strptime(prof["time"], "%Y-%m-%dT%H:%MZ")
    lines = [
        "%TITLE%",
        f" {prof['station']}   {dt:%y%m%d}/{dt:%H}00",
        "   LEVEL      HGHT       TEMP       DWPT       WDIR       WSPD",
        "-" * 66,
        "%RAW%",
    ]
    for r in prof["levels"]:
        lines.append(
            f"{r['p']:7.1f},{r['z'] or 0:10.1f},{r['t']:10.1f},"
            f"{(r['td'] if r['td'] is not None else -9999):10.1f},"
            f"{(r['wd'] if r['wd'] is not None else -9999):10.1f},"
            f"{(r['ws'] * 1.94384 if r['ws'] is not None else -9999):10.1f}"
        )
    lines.append("%END%")
    return "\n".join(lines) + "\n"
