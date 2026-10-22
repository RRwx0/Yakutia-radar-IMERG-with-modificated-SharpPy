from server.sounding import profile, times

print("times 2011:", len(times("24959", 2011)))
p = profile("24959", "2020-06-01T12:00Z")
if not p:
    print("no profile")
else:
    print(p["name"], p["time"], p["source"], len(p["levels"]))
    print(p["levels"][:3])
    print(p["indices"])
