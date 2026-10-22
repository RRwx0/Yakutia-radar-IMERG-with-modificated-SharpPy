import sys, traceback, urllib.request, os
sys.path.insert(0, ".")
from datetime import datetime, timezone
from radar.sources import gfs

when = datetime.now(timezone.utc)
date, cycle = gfs._cycle(when)
print("cycle", date, cycle)
url = gfs._url(date, cycle, 0)
print(url[:160])
path = os.path.join(os.environ["TEMP"], "gfs_multi.grib2")
try:
    with urllib.request.urlopen(url, timeout=90) as r, open(path, "wb") as f:
        f.write(r.read())
    print("bytes", os.path.getsize(path))
    head = open(path, "rb").read(20)
    print("head", head[:10])
    import cfgrib
    sets = cfgrib.open_datasets(path)
    for ds in sets:
        print("DATASET", list(ds.data_vars), list(ds.dims), ds.attrs.get("GRIB_shortName"))
except Exception as e:
    traceback.print_exc()
