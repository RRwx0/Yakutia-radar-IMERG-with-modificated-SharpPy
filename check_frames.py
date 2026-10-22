import json, sys
sys.stdout.reconfigure(encoding="utf-8")
m = json.load(open("data/manifest.json", encoding="utf-8"))
for f in m["frames"][:2] + m["frames"][-2:]:
    print(f["id"], f["time"], f["stats"].get("echo_pct"), f["zoom_tiles"])
