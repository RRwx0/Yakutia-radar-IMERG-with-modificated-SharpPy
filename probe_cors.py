import urllib.request

url = "https://api.open-meteo.com/v1/forecast?latitude=62.04&longitude=129.68&current=wind_speed_10m,wind_gusts_10m,wind_direction_10m,temperature_2m,weather_code&wind_speed_unit=ms&timezone=Asia/Yakutsk"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 yakutia-radar", "Origin": "https://rrwx0.github.io"})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print("status:", r.status)
        print("access-control-allow-origin:", r.headers.get("Access-Control-Allow-Origin"))
        print("access-control-allow-methods:", r.headers.get("Access-Control-Allow-Methods"))
        body = r.read().decode("utf-8")
        print("body:", body[:300])
except Exception as e:
    print("ERR", type(e).__name__, str(e)[:160])