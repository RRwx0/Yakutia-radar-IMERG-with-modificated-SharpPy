import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from radar.config import FRAME_MINUTES
from radar.grid import Grid
from radar.pipeline import _iso, _stats
from radar.sources import imerg
from radar.tiles import render_all_zooms

ARCHIVE = Path("data/archive")
TILES = Path("client/tiles")
GRID = Grid()

manifests = sorted(ARCHIVE.glob("*.json"))
print("manifests:", len(manifests))

for mf in manifests:
    manifest = json.loads(mf.read_text(encoding="utf-8"))
    arch = manifest["archive"]
    date, hour = arch["date"], int(arch["hour"])
    key = arch.get("key") or mf.stem
    end = datetime.fromisoformat(date).replace(tzinfo=timezone.utc) + timedelta(hours=hour)
    times = [end - timedelta(minutes=FRAME_MINUTES * (11 - i)) for i in range(12)]

    ok = True
    for i, when in enumerate(times):
        fid = f"a{date.replace('-', '')}T{int(hour):02d}_{i:02d}"
        # если тайлы уже есть и манифест сходится — пропускаем
        if (TILES / fid).exists():
            continue
        try:
            field = imerg.fetch_field(GRID, when)
            render_all_zooms(GRID, field, TILES / fid)
            print("ok", fid)
        except Exception as e:
            print("ERR", fid, type(e).__name__, e)
            ok = False
            break
        time.sleep(0.5)

    if ok:
        print("DONE", key)
    else:
        print("FAILED", key)

print("tiles dirs now:", len([p for p in TILES.iterdir() if p.is_dir()]))