import pathlib
p = pathlib.Path("radar/config.py")
s = p.read_text(encoding="utf-8")
s = s.replace("OBS_FRAMES = 12\nFRAME_MINUTES = 10\nNOWCAST_STEPS = 6", "OBS_FRAMES = 12\nFRAME_MINUTES = 30\nNOWCAST_STEPS = 4")
s = s.replace("TILE_ZOOMS = (4, 5, 6)", "TILE_ZOOMS = (4, 5, 6)\nSOURCE = \"imerg\"")
p.write_text(s, encoding="utf-8")
print(s[s.find("OBS_FRAMES"):s.find("OBS_FRAMES")+120])
