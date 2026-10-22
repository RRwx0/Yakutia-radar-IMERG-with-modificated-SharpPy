import pathlib
p = pathlib.Path("radar/pipeline.py")
s = p.read_text(encoding="utf-8")
old = '''    result = forecast(mosaics, steps=NOWCAST_STEPS, members=5)
    last_skill = {}
    if len(mosaics) > 1:
        u_s, v_s = estimate_flow(mosaics[-2], mosaics[-1])
        last_skill = skill(mosaics[-2], advect(mosaics[-2], u_s, v_s), mosaics[-1])'''
new = '''    method = "advection"
    last_skill = {}
    if len(mosaics) > 1:
        u_s, v_s = estimate_flow(mosaics[-2], mosaics[-1])
        last_skill = skill(mosaics[-2], advect(mosaics[-2], u_s, v_s), mosaics[-1])
        adv_mae = last_skill.get("advection_mae", 1e9)
        per_mae = last_skill.get("persistence_mae", 1e9)
        if adv_mae >= 0.98 * per_mae:
            method = "persistence"

    result = forecast(mosaics, steps=NOWCAST_STEPS, members=5, method=method)'''
assert old in s
s = s.replace(old, new)
s = s.replace('"nowcast": {\n            "members": result["members"],', '"nowcast": {\n            "method": method,\n            "members": result["members"],')
p.write_text(s, encoding="utf-8")
print("patched")
