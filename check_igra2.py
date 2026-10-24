import zipfile
from pathlib import Path

for wmo in ["30710", "21432"]:
    p = Path(f"data/igra/RSM000{wmo}.zip")
    if not p.exists():
        print(wmo, "no zip")
        continue
    with zipfile.ZipFile(p) as z:
        name = z.namelist()[0]
        raw = z.read(name).decode("utf-8", "replace")
    lines = raw.splitlines()
    print(wmo, "file:", name, "lines:", len(lines))
    print("  first:", lines[0][:80])
    print("  second:", lines[1][:80])
    # считаем заголовки с датой
    import re
    hdr = re.compile(r"^#\S+\s+(\d{4})")
    years = {}
    for line in lines:
        m = hdr.match(line)
        if m:
            y = int(m.group(1))
            years[y] = years.get(y, 0) + 1
    sorted_years = sorted(years.items())
    print("  years:", sorted_years[:2], "...", sorted_years[-2:] if len(sorted_years) > 2 else "", "total years:", len(years))