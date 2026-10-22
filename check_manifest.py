import json
import os

m = json.load(open("data/manifest.json", encoding="utf-8"))
print("tile_version", m.get("tile_version"))
print("phase", m["phase"])
print("severe", m["frames"][-1]["stats"]["severe"]["score"], "cells", len(m["frames"][-1]["cells"]))
d = open("client/data.js", encoding="utf-8").read()
print("data.js MB", round(os.path.getsize("client/data.js") / 1048576, 2))
print("wetbulb", "wetbulb" in d, "phase", '"phase"' in d)
print("tiles MB", round(sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk("client/tiles") for f in fs) / 1048576, 2))
