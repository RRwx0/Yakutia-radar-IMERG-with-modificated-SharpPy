import json
import time
from pathlib import Path

from server import sounding as snd

CITY_STATIONS = {
    "Якутск": "24959", "Верхоянск": "24266", "Оймякон": "24688",
    "Вилюйск": "24908", "Олёкминск": "30710", "Хандыга": "24944",
    "Тикси": "21432", "Черский": "25123",
}

RECENT_N = 12


def valid_profiles(wmo, times_list, limit):
    out = []
    for iso in reversed(times_list):
        try:
            p = snd.profile(wmo, iso)
        except Exception:
            p = None
        if p:
            out.append((iso, p))
            if len(out) >= limit:
                break
        time.sleep(0.15)
    return out


stations = [{"wmo": k, "name": v[0], "lat": v[1], "lon": v[2]} for k, v in snd.STATIONS.items()]
latest = {}
recent = []
meta = {}

for city, wmo in CITY_STATIONS.items():
    zpath = snd._zip_path(wmo)
    if not zpath.exists() or zpath.stat().st_size < 1_000_000:
        meta[wmo] = {"city": city, "status": "no_archive"}
        print(city, "no archive")
        continue
    try:
        t = snd.times(wmo, None)
    except Exception as e:
        meta[wmo] = {"city": city, "status": "error", "detail": str(e)[:80]}
        print(city, "times err", e)
        continue
    if not t:
        meta[wmo] = {"city": city, "status": "empty"}
        print(city, "no times")
        continue
    last = t[-1]
    lp = None
    try:
        lp = snd.profile(wmo, last)
    except Exception:
        lp = None
    if lp:
        latest[wmo] = lp
        meta[wmo] = {"city": city, "status": "fresh", "latest": last}
        print(city, "latest:", last, "levels:", len(lp["levels"]))
    else:
        meta[wmo] = {"city": city, "status": "old", "latest": last}
        print(city, "profile empty for latest:", last)
    # последние N валидных профилей
    for iso, p in reversed(valid_profiles(wmo, t, RECENT_N)):
        recent.append({"wmo": wmo, "time": iso, "profile": p})
    print("   recent profiles:", len(recent))

out = {
    "stations": stations,
    "latest": latest,
    "recent": recent,
    "city_stations": CITY_STATIONS,
    "meta": meta,
    "note": "Данные зондирований Росгидромета через архивы IGRA v2.2 (NOAA NCEI). Для Олёкминска, Хандыги и Тикси свежие данные отсутствуют.",
}

root = Path("client")
snd_js = root / "snd_data.js"
snd_js.write_text("\nwindow.RADAR_SND=" + json.dumps(out, ensure_ascii=False) + ";\n", encoding="utf-8")
print("snd_data.js", snd_js.stat().st_size, "bytes | latest:", len(latest), "| recent:", len(recent))