import pathlib
p = pathlib.Path("server/app.py")
s = p.read_text(encoding="utf-8")
s = s.replace('TILES = CLIENT / "tiles"\nCLIENT = ROOT / "client"', 'CLIENT = ROOT / "client"\nTILES = CLIENT / "tiles"')
if 'CLIENT = ROOT / "client"\nTILES' not in s:
    s = s.replace('TILES = CLIENT / "tiles"', 'CLIENT = ROOT / "client"\nTILES = CLIENT / "tiles"')
    s = s.replace('CLIENT = ROOT / "client"\n\napp', '\napp')
p.write_text(s, encoding="utf-8")
print([l for l in s.splitlines()[:20] if "CLIENT" in l or "TILES" in l])
