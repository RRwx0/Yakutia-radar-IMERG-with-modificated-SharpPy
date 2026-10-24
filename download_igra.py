import time
from pathlib import Path

import requests

from server import sounding as snd

TARGETS = ["24959", "24266", "24688", "24908", "30710", "24944", "21432", "25123"]

for wmo in TARGETS:
    path = snd._zip_path(wmo)
    if path.exists() and path.stat().st_size > 1_000_000:
        print("already have", wmo, path.stat().st_size // 1_000_000, "MB")
        continue
    igra_id = snd.igra_id(wmo)
    url = f"{snd.IGRA_BASE}/{igra_id}-data.txt.zip"
    print("downloading", wmo, url)
    for attempt in range(3):
        try:
            with requests.get(url, stream=True, timeout=600, headers={"User-Agent": "Mozilla/5.0"}) as r:
                r.raise_for_status()
                with open(path, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
            print("ok", wmo, path.stat().st_size // 1_000_000, "MB")
            break
        except Exception as e:
            print("attempt", attempt + 1, "failed:", type(e).__name__, str(e)[:120])
            time.sleep(3)
    else:
        print("FAILED", wmo)