import pathlib
p = pathlib.Path("radar/nowcast.py")
s = p.read_text(encoding="utf-8")
s = s.replace('''    mask = np.isfinite(truth) & (truth > 5.0)''', '''    mask = np.isfinite(truth) & np.isfinite(persistence) & np.isfinite(forecasted) & (truth > 5.0)''')
p.write_text(s, encoding="utf-8")
print("ok")
