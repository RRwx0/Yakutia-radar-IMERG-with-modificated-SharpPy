import pathlib
p = pathlib.Path("radar/pipeline.py")
s = p.read_text(encoding="utf-8")

s = s.replace("from .sources import imerg", "from .sources import gfs, imerg\nfrom .cells import detect_cells, severe_proxy")
s = s.replace("    PROBE,\n    STATIONS,", "    DATA,\n    PROBE,\n    STATIONS,")

s = s.replace('''    visibility_pct = 100.0
''', '''    visibility_pct = 100.0

    env = gfs.fetch(grid, times[-1])
    if env is not None:
        np.savez_compressed(
            DATA / "env.npz",
            t2m=env["t2m"].astype(np.float32),
            cape=env["cape"].astype(np.float32),
            shear=env["shear"].astype(np.float32),
        )
''')

s = s.replace('''        stats = _stats(frame["field"])
''', '''        stats = _stats(frame["field"])
        cells = detect_cells(frame["field"], grid.lats, grid.lons)
        stats["cells"] = len(cells)
        if cells:
            stats["top_cell"] = cells[0]
        if env is not None:
            idxs = grid.nearest_index(cells[0]["lat"], cells[0]["lon"]) if cells else (grid.ny // 2, grid.nx // 2)
            stats["severe"] = severe_proxy(
                cells,
                float(env["cape"][idxs]),
                float(env["shear"][idxs]),
            )
''')

s = s.replace('''                "stats": stats,
''', '''                "stats": stats,
                "cells": cells,
''')
p.write_text(s, encoding="utf-8")
print("ok", s.count("detect_cells"), s.count("env = gfs.fetch"))
