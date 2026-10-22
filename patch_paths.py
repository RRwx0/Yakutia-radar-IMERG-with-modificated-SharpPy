import pathlib
p = pathlib.Path("server/app.py")
s = p.read_text(encoding="utf-8")
s = s.replace('TILES = DATA / "tiles"', 'TILES = CLIENT / "tiles"')
p.write_text(s, encoding="utf-8")

p = pathlib.Path("client/app.js")
s = p.read_text(encoding="utf-8")
s = s.replace('const basePath = IS_FILE ? "../data/tiles/" + frame.id : "/tiles/" + frame.id;', 'const basePath = "tiles/" + frame.id;')
p.write_text(s, encoding="utf-8")
print("ok")
