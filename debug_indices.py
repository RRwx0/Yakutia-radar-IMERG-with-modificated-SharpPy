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

steps = [
    ("mu", lambda: mpcalc.most_unstable_parcel(P, T, TD, depth=300 * units.hPa)),
    ("parcel_profile", lambda: mpcalc.parcel_profile(P, 15.6 * units.degC, -1.4 * units.degC)),
    ("cape_cin", lambda: mpcalc.cape_cin(P, T, TD, mpcalc.parcel_profile(P, 15.6 * units.degC, -1.4 * units.degC))),
    ("mu_cape", lambda: mpcalc.most_unstable_cape_cin(P, T, TD)),
    ("pw", lambda: mpcalc.precipitable_water(P, TD)),
    ("li", lambda: mpcalc.lifted_index(P, T, mpcalc.parcel_profile(P, 15.6 * units.degC, -1.4 * units.degC))),
]
for name, fn in steps:
    try:
        out = fn()
        print(name, "OK", out if name != "li" else out[:3])
    except Exception:
        print("FAIL", name)
        traceback.print_exc()
