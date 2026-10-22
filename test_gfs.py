from netCDF4 import Dataset
url = "https://nomads.ncep.noaa.gov/dods/gfs_0p25/gfs20261017/gfs_0p25_00z"
try:
    ds = Dataset(url)
    names = [n for n in ds.variables if n in ("tmp2m","cape","dpt2m","ugrd10m","vgrd10m","ugrd500","vgrd500","hlcy","shear")]
    print("vars:", names)
    v = ds.variables["tmp2m"]
    print("tmp2m shape", v.shape, "dims", v.dimensions)
    print("lat range", ds.variables["lat"][0], ds.variables["lat"][-1], "lon", ds.variables["lon"][0], ds.variables["lon"][-1])
    ds.close()
except Exception as e:
    print("ERR", type(e).__name__, str(e)[:300])
