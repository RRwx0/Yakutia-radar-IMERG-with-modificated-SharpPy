import urllib.request

UA = {"User-Agent": "Mozilla/5.0 yakutia-radar probe"}
L = "IMERG_Precipitation_Rate_30min"
tmpl = f"https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/{L}/{{t}}/GoogleMapsCompatible_Level6/5/8/27.png"


def test(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
            d = r.read()
            return r.status, r.headers.get("Content-Type", ""), len(d)
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type", ""), len(e.read())


for t in ["default", "2026-10-22T18:00:00.000Z"]:
    s, ct, n = test(tmpl.format(t=t))
    print(t, "->", s, ct, n)