import json
import urllib.request

# Open-Meteo current weather: ветер, температура, снег по городам Якутии
cities = [
    ("Якутск", 62.0355, 129.6755),
    ("Оймякон", 63.4629, 142.7906),
    ("Верхоянск", 67.5539, 133.3898),
    ("Тикси", 71.6390, 128.8694),
    ("Мирный", 62.5353, 113.9611),
    ("Нерюнгри", 56.6584, 124.7250),
    ("Ленск", 60.7253, 114.9277),
    ("Вилюйск", 63.7517, 121.6241),
]
for name, lat, lon in cities:
    url = ("https://api.open-meteo.com/v1/forecast?latitude=%.4f&longitude=%.4f"
           "&current=temperature_2m,wind_speed_10m,wind_direction_10m,wind_gusts_10m,weather_code,snowfall"
           "&wind_speed_unit=ms&timezone=Asia/Yakutsk") % (lat, lon)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 yakutia-radar"})
        with urllib.request.urlopen(req, timeout=30) as r:
            j = json.loads(r.read())
        c = j["current"]
        print("%s: t=%s, wind=%s m/s dir=%s gust=%s code=%s" % (
            name, c.get("temperature_2m"), c.get("wind_speed_10m"),
            c.get("wind_direction_10m"), c.get("wind_gusts_10m"), c.get("weather_code")))
    except Exception as e:
        print(name, "ERR", type(e).__name__, str(e)[:80])