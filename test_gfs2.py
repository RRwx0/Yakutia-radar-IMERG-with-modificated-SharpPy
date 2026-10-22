import urllib.request, os
base = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl"
params = ("?file=gfs.t00z.pgrb2.0p25.f000&lev_2_m_above_ground=on&var_TMP=on"
          "&subregion=&leftlon=100&rightlon=170&toplat=76&bottomlat=50&dir=%2Fgfs.20261017%2F00%2Fatmos")
url = base + params
path = os.path.join(os.environ["TEMP"], "gfs_tmp.grib2")
try:
    with urllib.request.urlopen(url, timeout=60) as r, open(path, "wb") as f:
        f.write(r.read())
    print("bytes", os.path.getsize(path))
    import xarray as xr
    ds = xr.open_dataset(path, engine="cfgrib")
    print(ds)
    print(float(ds.t2m.min()), float(ds.t2m.max()))
except Exception as e:
    print("ERR", type(e).__name__, str(e)[:400])
