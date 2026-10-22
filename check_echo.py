import json, sys
sys.stdout.reconfigure(encoding="utf-8")
m = json.load(open("data/manifest.json", encoding="utf-8"))
print("focus", m["focus"])
for f in m["frames"]:
    print(f["id"], f["time"], f["stats"].get("echo_pct"), f["stats"].get("max_dbz"))
