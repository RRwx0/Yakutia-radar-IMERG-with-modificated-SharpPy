import re
import urllib.request

base = "https://rrwx0.github.io/Yakutia-radar-IMERG-with-modificated-SharpPy/"

sh = urllib.request.urlopen(base + "sharppy.html", timeout=60).read().decode("utf-8", "replace")
print("sharppy.html size:", len(sh))
# какие fetch к API делает sharppy
for m in re.findall(r'fetch\((["\'])([^"\']+)\1', sh):
    print("  fetch:", m[1])
print("inline scripts:", sh.count("<script"))

idx = urllib.request.urlopen(base + "index.html", timeout=60).read().decode("utf-8", "replace")
print()
print("index API_BASE:", re.findall(r'API_BASE\s*=\s*["\']?([^"\';\s]*)', idx))
print("fetch api/archive in app.js:")
app = urllib.request.urlopen(base + "app.js", timeout=60).read().decode("utf-8", "replace")
for m in re.findall(r'fetch\((["\'])([^"\']+)\1', app):
    print("  ", m[1])