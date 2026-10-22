import json
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8080"


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=120) as r:
        return r.status, r.read()


st, body = get("/api/sounding/times?station=24959&year=2020")
times = json.loads(body)["times"]
print("times", st, len(times), times[:2])

t = times[0]
q = urllib.parse.quote(t)
st, body = get(f"/api/sounding/profile?station=24959&time={q}")
prof = json.loads(body)
print("profile", st, prof["name"], prof["time"], len(prof["levels"]))
print("indices", prof["indices"])
print("td levels", sum(1 for x in prof["levels"] if x["td"] is not None))

st, body = get(f"/api/sounding/snd?station=24959&time={q}")
print("snd", st, len(body), body[:60])

st, body = get("/sharppy.html")
print("page", st, len(body))
