from pathlib import Path

import cfgrib

files = sorted(Path("data/cache/gfs").glob("gfs_*.grib2"), key=lambda p: p.stat().st_size)[-1]
print("file", files.name, round(files.stat().st_size / 1048576, 1), "MB")
for ds in cfgrib.open_datasets(str(files)):
    print("vars", list(ds.data_vars), "coords", list(ds.coords))
    if "isobaricInhPa" in ds.coords:
        print("  levels", ds["isobaricInhPa"].values)
