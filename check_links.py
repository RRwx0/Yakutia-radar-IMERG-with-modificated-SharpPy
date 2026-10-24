import re
import urllib.request

base = "https://rrwx0.github.io/Yakutia-radar-IMERG-with-modificated-SharpPy/"


def get(p):
    try:
        r = urllib.request.urlopen(base + p, timeout=60)
        return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return "ERR", str(e)


for p in ["", "sharppy.html", "archive.html"]:
    s, body = get(p)
    print(p or "/", s, len(body))

s, idx = get("index.html")
print("archive links:", re.findall(r'href="([^"]*(?:archive|sharppy)[^"]*)"', idx))
print("sharppy links:", re.findall(r'href="([^"]*sharppy[^"]*)"', idx))
print("modes link sharppy:", "sharppy" in idx.lower())