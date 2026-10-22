from pathlib import Path

app = Path("client/app.js")
s = app.read_text(encoding="utf-8")
s = s.replace('fetch("/api/probe?', 'fetch(API + "/api/probe?')
s = s.replace('fetch("/api/accum?', 'fetch(API + "/api/accum?')
s = s.replace('fetch("/api/state"', 'fetch(API + "/api/state"')
app.write_text(s, encoding="utf-8")
print("probe", s.count('API + "/api/probe'), "accum", s.count('API + "/api/accum'), "state", s.count('API + "/api/state'))

html = Path("client/index.html")
h = html.read_text(encoding="utf-8")
if 'src="config.js"' not in h:
    h = h.replace('<script src="data.js"></script>', '<script src="config.js"></script>\n<script src="data.js"></script>')
    html.write_text(h, encoding="utf-8")
print("config", h.count("config.js"))
