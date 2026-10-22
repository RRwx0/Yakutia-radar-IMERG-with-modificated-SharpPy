import pathlib
p = pathlib.Path("radar/pipeline.py")
s = p.read_text(encoding="utf-8")
s = s.replace('''        env_payload = {
            "t2m": [round(float(v), 1) for v in ct.ravel()],''', '''        env_payload = {
            "step": 0.5,
            "lat0": coarse.lat_min,
            "lon0": coarse.lon_min,
            "ny": coarse.ny,
            "nx": coarse.nx,
            "t2m": [round(float(v), 1) for v in ct.ravel()],''')
p.write_text(s, encoding="utf-8")
print("ok")
