import pathlib
p = pathlib.Path("radar/sources/imerg.py")
s = p.read_text(encoding="utf-8")
s = s.replace("rate[alpha.reshape(canvas.shape) < 20] = 0.0", "rate[alpha.reshape(canvas.shape[:2]) < 20] = 0.0")
p.write_text(s, encoding="utf-8")
print("ok")
