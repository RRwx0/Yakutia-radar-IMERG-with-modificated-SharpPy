import pathlib
p = pathlib.Path("radar/pipeline.py")
s = p.read_text(encoding="utf-8")

s = s.replace('''        "coverage_pct": round(visibility_pct, 2),''', '''        "coverage_pct": round(visibility_pct, 2),
        "env": {
            "available": env is not None,
            "t2m_min": round(float(np.nanmin(env["t2m"])), 1) if env is not None else None,
            "t2m_max": round(float(np.nanmax(env["t2m"])), 1) if env is not None else None,
            "cape_max": round(float(np.nanmax(env["cape"])), 0) if env is not None else None,
            "shear_max": round(float(np.nanmax(env["shear"])), 1) if env is not None else None,
        },''')

s = s.replace('''        embedded["frames"][frame["id"]] = [
            None if not np.isfinite(v) else round(float(v), 1) for v in arr.ravel()
        ]''', '''        embedded["frames"][frame["id"]] = [
            None if not np.isfinite(v) else round(float(v), 1) for v in arr.ravel()
        ]
        if env is not None:
            mask = (arr >= 5.0) & (coarse.sample(env["t2m"], coarse.lat2d, coarse.lon2d) <= 0.5)
            embedded.setdefault("phase", {})[frame["id"]] = mask.ravel().astype(int).tolist()''')

s = s.replace('''    payload = {"manifest": manifest, "probe": embedded}''', '''    env_payload = None
    if env is not None:
        ct = coarse.sample(env["t2m"], coarse.lat2d, coarse.lon2d)
        cc = coarse.sample(env["cape"], coarse.lat2d, coarse.lon2d)
        cs = coarse.sample(env["shear"], coarse.lat2d, coarse.lon2d)
        env_payload = {
            "t2m": [round(float(v), 1) for v in ct.ravel()],
            "cape": [round(float(v), 0) for v in cc.ravel()],
            "shear": [round(float(v), 1) for v in cs.ravel()],
        }
    payload = {"manifest": manifest, "probe": embedded, "env": env_payload}''')
p.write_text(s, encoding="utf-8")
print("ok", "env_payload" in s, "phase" in s)
