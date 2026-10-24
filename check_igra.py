from server import sounding as snd

for wmo, (name, lat, lon) in snd.STATIONS.items():
    zpath = snd._zip_path(wmo)
    if not zpath.exists() or zpath.stat().st_size < 1_000_000:
        print(wmo, name, "NO ARCHIVE")
        continue
    try:
        t = snd.times(wmo, None)
        latest = t[-1] if t else None
        n2026 = sum(1 for x in t if x.startswith("2026"))
        print(wmo, name, "| total:", len(t), "| 2026:", n2026, "| latest:", latest)
    except Exception as e:
        print(wmo, name, "ERR", type(e).__name__, str(e)[:80])