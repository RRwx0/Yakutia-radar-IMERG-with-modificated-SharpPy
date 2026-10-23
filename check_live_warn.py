import urllib.request

base = "https://rrwx0.github.io/Yakutia-radar-IMERG-with-modificated-SharpPy/"
body = urllib.request.urlopen(base, timeout=60).read().decode("utf-8", "replace")
print("status bytes", len(body))
for tag in ["warnToggle", "warnPanel", "warnList"]:
    print(tag, tag in body)
app = urllib.request.urlopen(base + "app.js", timeout=60).read().decode("utf-8", "replace")
print("app.js warn code", "loadWarnings" in app and "warnLayer" in app)