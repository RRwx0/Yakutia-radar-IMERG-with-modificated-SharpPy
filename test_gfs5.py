import urllib.request, os
base = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl"
tests = {
 "multi": "?file=gfs.t00z.pgrb2.0p25.f000&lev_2_m_above_ground=on&var_TMP=on&lev_surface=on&var_CAPE=on&lev_10_m_above_ground=on&var_UGRD=on&var_VGRD=on&lev_500_mb=on&var_UGRD=on&var_VGRD=on&subregion=&leftlon=100&rightlon=170&toplat=76&bottomlat=50&dir=%2Fgfs.20261017%2F00%2Fatmos",
 "cape": "?file=gfs.t00z.pgrb2.0p25.f000&lev_surface=on&var_CAPE=on&subregion=&leftlon=100&rightlon=170&toplat=76&bottomlat=50&dir=%2Fgfs.20261017%2F00%2Fatmos",
 "winds": "?file=gfs.t00z.pgrb2.0p25.f000&lev_10_m_above_ground=on&var_UGRD=on&var_VGRD=on&subregion=&leftlon=100&rightlon=170&toplat=76&bottomlat=50&dir=%2Fgfs.20261017%2F00%2Fatmos",
 "w500": "?file=gfs.t00z.pgrb2.0p25.f000&lev_500_mb=on&var_UGRD=on&var_VGRD=on&subregion=&leftlon=100&rightlon=170&toplat=76&bottomlat=50&dir=%2Fgfs.20261017%2F00%2Fatmos",
}
for k, p in tests.items():
    try:
        with urllib.request.urlopen(base + p, timeout=60) as r:
            data = r.read()
        print(k, len(data), data[:4])
    except Exception as e:
        print(k, "ERR", e)
