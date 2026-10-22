import pathlib
p = pathlib.Path("radar/pipeline.py")
s = p.read_text(encoding="utf-8")

start = s.index("def run(regenerate: bool = True) -> dict:")
end = s.index("    result = forecast(mosaics")
new = '''def run(regenerate: bool = True) -> dict:
    started = time.time()
    grid = Grid()
    times = imerg.frames(OBS_FRAMES)
    mosaics = [imerg.fetch_field(grid, t) for t in times]
    echo_pct = float(np.mean([100.0 * np.isfinite(m).mean() for m in mosaics]))
    visibility_pct = 100.0

'''
s = s[:start] + new + s[end:]
s = s.replace("from .sources import synthetic\n", "from .sources import imerg\n")
s = s.replace('"stations": [\n            {\n                "id": s.id,\n                "name": s.name,\n                "lat": s.lat,\n                "lon": s.lon,\n                "range_km": s.range_km,\n                "band": s.band,\n                "beam_deg": s.beam_deg,\n                "status": "simulated",\n            }\n            for s in STATIONS\n        ],', '"stations": [],')
s = s.replace('"source": "simulated DMRL-S volumes (C-band, 250 km, 10 min)",', '"source": imerg.describe(),\n        "echo_coverage_pct": round(echo_pct, 2),')
p.write_text(s, encoding="utf-8")
print(s[s.index("def run"):s.index("def run")+700])
