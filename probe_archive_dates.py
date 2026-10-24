import urllib.request

UA = {"User-Agent": "Mozilla/5.0 yakutia-radar probe"}
L = "IMERG_Precipitation_Rate_30min"


def test(t, tile="5/8/27"):
    url = f"https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/{L}/{t}/GoogleMapsCompatible_Level6/{tile}.png"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
            d = r.read()
            return r.status, r.headers.get("Content-Type", ""), len(d)
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type", ""), len(e.read() or b"")


for t in [
    "2020-07-15T12:00:00Z",
    "2020-07-15T12:00:00.000Z",
    "2021-01-10T06:00:00Z",
    "2022-02-15T00:00:00Z",
    "2023-07-15T12:00:00Z",
    "2024-07-15T12:00:00.000Z",
    "2026-10-22T18:00:00.000Z",
]:
    s, ct, n = test(t)
    print(t, "->", s, ct, n)