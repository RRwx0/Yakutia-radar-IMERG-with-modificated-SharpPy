import pathlib
p = pathlib.Path("radar/config.py")
s = p.read_text(encoding="utf-8")
s = s.replace("TILE_ZOOMS = (4, 5, 6)", "TILE_ZOOMS = (3, 4, 5, 6)")
p.write_text(s, encoding="utf-8")

p = pathlib.Path("radar/pipeline.py")
s = p.read_text(encoding="utf-8")
anchor = '    manifest = {\n'
add = '''    focus = None
    last = mosaics[-1]
    wet = np.isfinite(last) & (last >= 20.0)
    if wet.any():
        iy, ix = np.where(wet)
        lat_hi = float(grid.lats[min(grid.ny - 1, iy.max() + 20)])
        lat_lo = float(grid.lats[max(0, iy.min() - 20)])
        lon_hi = float(grid.lons[min(grid.nx - 1, ix.max() + 20)])
        lon_lo = float(grid.lons[max(0, ix.min() - 20)])
        focus = [[round(lat_lo, 2), round(lon_lo, 2)], [round(lat_hi, 2), round(lon_hi, 2)]]

    manifest = {
'''
assert anchor in s
s = s.replace(anchor, add, 1)
s = s.replace('"frames": manifest_frames,', '"focus": focus,\n        "frames": manifest_frames,')
p.write_text(s, encoding="utf-8")
print("ok")
