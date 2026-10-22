import pathlib
p = pathlib.Path("server/archive.py")
s = p.read_text(encoding="utf-8")
s = s.replace("    times = [end - timedelta(minutes=FRAME_MINUTES * (imerg.frames and 11 - i)) for i in range(12)]",
              "    times = [end - timedelta(minutes=FRAME_MINUTES * (11 - i)) for i in range(12)]")
s = s.replace("from radar.pipeline import CELL_KM2, _iso, _stats", "from radar.pipeline import _iso, _stats")
s = s.replace("\n    for old in TILES.glob(f\"a{date.replace('-', '')}T{int(hour):02d}_*\"):\n        pass\n", "")
p.write_text(s, encoding="utf-8")
print("ok")
