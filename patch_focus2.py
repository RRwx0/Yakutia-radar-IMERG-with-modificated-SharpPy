import pathlib
p = pathlib.Path("radar/pipeline.py")
s = p.read_text(encoding="utf-8")
old = '''    focus = None
    last = mosaics[-1]
    wet = np.isfinite(last) & (last >= 20.0)
    if wet.any():
        iy, ix = np.where(wet)
        lat_hi = float(grid.lats[min(grid.ny - 1, iy.max() + 20)])
        lat_lo = float(grid.lats[max(0, iy.min() - 20)])
        lon_hi = float(grid.lons[min(grid.nx - 1, ix.max() + 20)])
        lon_lo = float(grid.lons[max(0, ix.min() - 20)])
        focus = [[round(lat_lo, 2), round(lon_lo, 2)], [round(lat_hi, 2), round(lon_hi, 2)]]
'''
new = '''    focus = None
    last = mosaics[-1]
    wet = np.isfinite(last) & (last >= 30.0)
    if wet.any():
        iy, ix = np.where(wet)
        cy = int(np.median(iy))
        cx = int(np.median(ix))
        lat_c = float(grid.lats[cy])
        lon_c = float(grid.lons[cx])
        focus = [
            [round(max(grid.lat_min, lat_c - 4.0), 2), round(max(grid.lon_min, lon_c - 7.0), 2)],
            [round(min(grid.lat_max, lat_c + 4.0), 2), round(min(grid.lon_max, lon_c + 7.0), 2)],
        ]
'''
assert old in s
s = s.replace(old, new)
p.write_text(s, encoding="utf-8")

p = pathlib.Path("radar/colormap.py")
s = p.read_text(encoding="utf-8")
s = s.replace("def colorize(dbz: np.ndarray, alpha: int = 210) -> np.ndarray:", "def colorize(dbz: np.ndarray, alpha: int = 235) -> np.ndarray:")
p.write_text(s, encoding="utf-8")
print("ok")
