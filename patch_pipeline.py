import pathlib
p = pathlib.Path("radar/pipeline.py")
s = p.read_text(encoding="utf-8")
s = s.replace("from .nowcast import forecast, skill", "from .nowcast import advect, estimate_flow, forecast, skill")
s = s.replace(
    '    last_skill = skill(mosaics[-2], mosaics[-1], mosaics[-1]) if len(mosaics) > 1 else {}',
    '    last_skill = {}\n'
    '    if len(mosaics) > 1:\n'
    '        u_s, v_s = estimate_flow(mosaics[-2], mosaics[-1])\n'
    '        last_skill = skill(mosaics[-2], advect(mosaics[-2], u_s, v_s), mosaics[-1])'
)
p.write_text(s, encoding="utf-8")
print("ok")
