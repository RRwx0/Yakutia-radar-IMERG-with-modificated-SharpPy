from pathlib import Path

p = Path("client/sharppy.html")
s = p.read_text(encoding="utf-8")
reps = [
    ('fetch("/api/sounding/stations")', 'fetch(API + "/api/sounding/stations")'),
    (
        "fetch(`/api/sounding/times?station=${st}&year=${yr}`)",
        "fetch(`${API}/api/sounding/times?station=${st}&year=${yr}`)",
    ),
    (
        "fetch(`/api/sounding/profile?station=${st}&time=${encodeURIComponent(time)}`)",
        "fetch(`${API}/api/sounding/profile?station=${st}&time=${encodeURIComponent(time)}`)",
    ),
    (
        "`/api/sounding/snd?station=${st}&time=${encodeURIComponent(time)}`",
        "`${API}/api/sounding/snd?station=${st}&time=${encodeURIComponent(time)}`",
    ),
    ("<script>\n(() => {", '<script src="config.js"></script>\n<script>\n(() => {'),
]
for a, b in reps:
    if a in s:
        s = s.replace(a, b)
    else:
        print("MISS", a[:60])
p.write_text(s, encoding="utf-8")
print("API+", s.count("API +"), "${API}", s.count("${API}"), "config", s.count("config.js"))
