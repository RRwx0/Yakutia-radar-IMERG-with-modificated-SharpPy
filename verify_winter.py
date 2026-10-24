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


s, win = get("winter.html")
print("winter.html:", s, len(win))
print("  branding:", "ЗИМНИЙ РАДАР" in win and "ноябрь–март" in win)
print("  winter flag:", 'class="winter"' in win)
print("  link to index:", 'href="index.html"' in win)
print("  link from index:")
s2, idx = get("index.html")
print("  index:", s2, 'href="winter.html"' in idx)
print("  sharppy+hud refs:", "снеговая ячейка" in win or "Метелевая" in win)

s3, app = get("app.js")
print("app.js:", s3, "| IS_WINTER:", "IS_WINTER" in app)
s4, css = get("styles.css")
print("styles.css:", s4, "| body.winter:", "body.winter" in css)