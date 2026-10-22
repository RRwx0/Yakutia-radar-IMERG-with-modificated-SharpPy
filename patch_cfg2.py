import pathlib
p = pathlib.Path("radar/config.py")
s = p.read_text(encoding="utf-8")
s = s.replace('DATA = ROOT / "data"', 'DATA = ROOT / "data"\nCLIENT = ROOT / "client"')
s = s.replace('TILES = DATA / "tiles"', 'TILES = CLIENT / "tiles"')
s = s.replace('CACHE = DATA / "cache"\n', 'CACHE = DATA / "cache"\n')
s = s.replace('CLIENT = ROOT / "client"\n\nLON_MIN', '\nLON_MIN')
p.write_text(s, encoding="utf-8")
print([l for l in s.splitlines() if "CLIENT" in l or "TILES" in l])
