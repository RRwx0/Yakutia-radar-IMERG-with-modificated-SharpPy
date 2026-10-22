import re
from pathlib import Path

s = Path("client/index.html").read_text(encoding="utf-8")
for m in re.finditer(r'<script[^>]*src="([^"]+)"', s):
    print(m.group(1))
print("--- tail scripts ---")
print(s[s.rfind("leaflet.js"):][:400])