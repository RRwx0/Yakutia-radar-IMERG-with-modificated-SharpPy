import pathlib
p = pathlib.Path("radar/nowcast.py")
s = p.read_text(encoding="utf-8")

s = s.replace(
'''def apply_correction(field: np.ndarray, u: np.ndarray, v: np.ndarray, w: np.ndarray) -> np.ndarray:
    speed = np.hypot(u, v)
    feats = _features(field, speed)
    delta = feats @ w
    return np.clip(field + delta, 0.0, 70.0)''',
'''def apply_correction(field: np.ndarray, u: np.ndarray, v: np.ndarray, w: np.ndarray) -> np.ndarray:
    speed = np.hypot(u, v)
    feats = _features(field, speed)
    delta = feats @ w
    out = np.clip(field + delta, 0.0, 70.0)
    return np.where(field > 3.0, out, field)''')

s = s.replace(
'''def forecast(
    mosaics: list[np.ndarray],
    steps: int = 6,
    members: int = 5,
    seed: int = 5,
) -> dict:''',
'''def forecast(
    mosaics: list[np.ndarray],
    steps: int = 6,
    members: int = 5,
    seed: int = 5,
    method: str = "advection",
) -> dict:''')

s = s.replace(
'''    u0, v0 = flows[-1] if flows else (np.zeros_like(mosaics[-1]), np.zeros_like(mosaics[-1]))''',
'''    u0, v0 = flows[-1] if flows else (np.zeros_like(mosaics[-1]), np.zeros_like(mosaics[-1]))
    if method == "persistence":
        u0 = np.zeros_like(u0)
        v0 = np.zeros_like(v0)''')

p.write_text(s, encoding="utf-8")
print("ok")
