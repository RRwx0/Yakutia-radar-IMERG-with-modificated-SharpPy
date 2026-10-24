import re
from pathlib import Path

html = Path("client/index.html").read_text(encoding="utf-8")
js = Path("client/app.js").read_text(encoding="utf-8")
ids_needed = set(re.findall(r'el\("([A-Za-z0-9_]+)"\)', js))
ids_html = set(re.findall(r'id="([A-Za-z0-9_]+)"', html))
missing = sorted(i for i in ids_needed if i not in ids_html)
print("ids used in app.js:", len(ids_needed))
print("MISSING in index.html:", missing)