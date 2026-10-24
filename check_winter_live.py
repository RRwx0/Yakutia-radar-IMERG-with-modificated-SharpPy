import urllib.request

for p in ["/", "/winter.html", "/winter_data.js", "/app.js",
          "/tiles/w20251225T12_11/5/27/8.png", "/tiles/w20251225T12_00/5/27/8.png"]:
    try:
        r = urllib.request.urlopen("http://127.0.0.1:8080" + p, timeout=30)
        print(p, r.status, len(r.read()))
    except Exception as e:
        print(p, "ERR", str(e)[:70])