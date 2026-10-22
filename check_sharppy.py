import io
import urllib.request as u
import zipfile

base = "http://127.0.0.1:8080/"
paths = [
    "sharppy.html",
    "sharppy/files/wx_launcher.py",
    "sharppy/files/sharppy_core.py",
    "sharppy/sharpy-hen1ch.zip",
]
for p in paths:
    r = u.urlopen(base + p, timeout=8)
    print(p, r.status, r.headers.get("Content-Length"))
    r.read()

b = u.urlopen(base + "sharppy/sharpy-hen1ch.zip", timeout=8).read()
z = zipfile.ZipFile(io.BytesIO(b))
print("zip names", z.namelist())
print("zip test", z.testzip())

h = u.urlopen(base, timeout=8).read().decode("utf-8")
print("button", "sharppy.html" in h, "blank", 'target="_blank"' in h)
