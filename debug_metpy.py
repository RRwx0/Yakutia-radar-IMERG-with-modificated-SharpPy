import traceback

import numpy as np
from metpy import calc as mpcalc
from metpy.units import units

from server.sounding import profile

p = profile("24959", "2020-06-01T12:00Z")
lev = p["levels"]
P = np.array([r["p"] for r in lev]) * units.hPa
T = np.array([r["t"] for r in lev]) * units.degC
TD = np.array([r["td"] for r in lev]) * units.degC
Z = np.array([r["z"] for r in lev]) * units.m
print("shapes", P.shape, T.shape, TD.shape)

for name, fn in [
    ("mu", lambda: mpcalc.most_unstable_parcel(P, T, TD, depth=300 * units.hPa)),
    ("lcl", lambda: mpcalc.lcl(P[0], T[0], TD[0])),
]:
    try:
        print(name, fn())
    except Exception:
        print("FAIL", name)
        traceback.print_exc()

try:
    pm, tm, tdm = mpcalc.most_unstable_parcel(P, T, TD, depth=300 * units.hPa)
    prof = mpcalc.parcel_profile(P, tm, tdm)
    print("parcel ok", prof[:3])
    print("cape", mpcalc.cape_cin(P, T, TD, prof))
except Exception:
    traceback.print_exc()
