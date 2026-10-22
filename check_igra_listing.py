import re

import requests

url = "https://www.ncei.noaa.gov/data/integrated-global-radiosonde-archive/access/data-por/"
r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
print(r.status_code, len(r.text))
links = re.findall(r'href="([^"]*24959[^"]*)"', r.text)
print("\n".join(links[:20]) or "no links")
