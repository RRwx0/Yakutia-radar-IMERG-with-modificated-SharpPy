import glob, cfgrib
p = sorted(glob.glob("data/cache/gfs/*.grib2"))[-1]
print(p)
for ds in cfgrib.open_datasets(p):
    print(list(ds.data_vars), list(ds.dims), {k: float(v) if v == v else v for k, v in (ds.coords.get("isobaricInhPa").values if "isobaricInhPa" in ds.coords else []).__class__ and {}} if False else "")
    if "isobaricInhPa" in ds.coords:
        print("  levels", ds["isobaricInhPa"].values)
