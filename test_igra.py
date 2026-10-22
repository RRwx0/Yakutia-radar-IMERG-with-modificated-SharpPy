import io
import zipfile
from pathlib import Path

import requests

url = "https://www.ncei.noaa.gov/pub/data/igra/data/data-por/RSM00024959-data.txt.zip"
out = Path("data/igra/RSM00024959.zip")
out.parent.mkdir(parents=True, exist_ok=True)
if not out.exists() or out.stat().st_size < 1_000_000:
    with requests.get(url, stream=True, timeout=300, headers={"User-Agent": "Mozilla/5.0"}) as r:
        r.raise_for_status()
        with open(out, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
print("size", out.stat().st_size)
with zipfile.ZipFile(out) as z:
    name = z.namelist()[0]
    print("member", name)
    with z.open(name) as f:
        raw = f.read().decode("utf-8", "replace")
lines = raw.splitlines()
print("lines", len(lines))
idx = next((i for i, l in enumerate(lines) if l.startswith("#") and "20200601" in l), None)
print("header idx", idx)
print("\n".join(lines[idx:idx + 4]))
