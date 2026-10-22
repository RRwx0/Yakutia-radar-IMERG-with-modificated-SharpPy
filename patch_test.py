import pathlib
p = pathlib.Path("test_mosaic.py")
s = p.read_text(encoding="utf-8")
s = s.replace("mosaic, coverage, nearest = build_mosaic(grid, scans)", "mosaic, coverage, nearest, visibility = build_mosaic(grid, scans)")
s = s.replace('print("coverage %", round(100 * (coverage > 0).mean(), 1), "max dbz", round(float(np.nanmax(mosaic)), 1))', 'print("radar visibility %", round(100 * (visibility > 0).mean(), 1))\n    print("precip coverage %", round(100 * (coverage > 0).mean(), 1), "max dbz", round(float(np.nanmax(mosaic)), 1))')
p.write_text(s, encoding="utf-8")
print("ok")
