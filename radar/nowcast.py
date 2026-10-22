from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates, uniform_filter, zoom

FLOW_SCALE = 4
FLOW_ITER = 90
FLOW_ALPHA = 1.4


def _downsample(a: np.ndarray, k: int) -> np.ndarray:
    h, w = a.shape
    h2, w2 = h // k * k, w // k * k
    return a[:h2, :w2].reshape(h2 // k, k, w2 // k, k).mean(axis=(1, 3))


def _upsample(a: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    zy = shape[0] / a.shape[0]
    zx = shape[1] / a.shape[1]
    return zoom(a, (zy, zx), order=1)[: shape[0], : shape[1]]


def estimate_flow(a: np.ndarray, b: np.ndarray, scale: int = FLOW_SCALE, iterations: int = FLOW_ITER) -> tuple[np.ndarray, np.ndarray]:
    a0 = gaussian_filter(_downsample(np.nan_to_num(a), scale), 1.0)
    b0 = gaussian_filter(_downsample(np.nan_to_num(b), scale), 1.0)
    mean = 0.5 * (a0 + b0)
    ix = np.gradient(mean, axis=1)
    iy = np.gradient(mean, axis=0)
    it = b0 - a0
    u = np.zeros_like(a0)
    v = np.zeros_like(a0)
    for _ in range(iterations):
        ubar = uniform_filter(u, 3)
        vbar = uniform_filter(v, 3)
        denom = FLOW_ALPHA**2 + ix**2 + iy**2
        u = ubar - ix * (ix * ubar + iy * vbar + it) / denom
        v = vbar - iy * (ix * ubar + iy * vbar + it) / denom
    return _upsample(u, a.shape) * scale, _upsample(v, a.shape) * scale


def advect(field: np.ndarray, u: np.ndarray, v: np.ndarray, dt: float = 1.0) -> np.ndarray:
    h, w = field.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    filled = np.nan_to_num(field, nan=0.0)
    out = map_coordinates(
        filled,
        [(yy - v * dt).ravel(), (xx - u * dt).ravel()],
        order=1,
        mode="constant",
        cval=0.0,
    ).reshape(h, w)
    return out.astype(np.float32)


def _features(advected: np.ndarray, speed: np.ndarray) -> np.ndarray:
    local = uniform_filter(np.nan_to_num(advected, nan=0.0), 5)
    return np.stack(
        [
            advected,
            local,
            speed,
            np.ones_like(advected),
        ],
        axis=-1,
    )


def fit_correction(pairs: list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]]) -> np.ndarray:
    rows = []
    targets = []
    for prev, actual, u, v in pairs:
        adv = advect(prev, u, v)
        speed = np.hypot(u, v)
        feats = _features(adv, speed)
        mask = np.isfinite(actual) & np.isfinite(adv) & (adv > 3.0)
        if mask.sum() < 2000:
            continue
        idx = np.flatnonzero(mask.ravel())
        if idx.size > 40000:
            idx = np.random.default_rng(3).choice(idx, 40000, replace=False)
        rows.append(feats.reshape(-1, 4)[idx])
        targets.append((actual - adv).ravel()[idx])
    if not rows:
        return np.zeros(4, dtype=np.float32)
    X = np.vstack(rows).astype(np.float64)
    y = np.concatenate(targets).astype(np.float64)
    xtx = X.T @ X + 1e-2 * np.eye(X.shape[1])
    xty = X.T @ y
    w = np.linalg.solve(xtx, xty)
    return w.astype(np.float32)


def apply_correction(field: np.ndarray, u: np.ndarray, v: np.ndarray, w: np.ndarray) -> np.ndarray:
    speed = np.hypot(u, v)
    feats = _features(field, speed)
    delta = feats @ w
    out = np.clip(field + delta, 0.0, 70.0)
    return np.where(field > 3.0, out, field)


def forecast(
    mosaics: list[np.ndarray],
    steps: int = 6,
    members: int = 5,
    seed: int = 5,
    method: str = "advection",
) -> dict:
    pairs = []
    flows = []
    for prev, nxt in zip(mosaics[:-1], mosaics[1:]):
        u, v = estimate_flow(prev, nxt)
        flows.append((u, v))
        pairs.append((prev, nxt, u, v))

    w = fit_correction(pairs)
    u0, v0 = flows[-1] if flows else (np.zeros_like(mosaics[-1]), np.zeros_like(mosaics[-1]))
    if method == "persistence":
        u0 = np.zeros_like(u0)
        v0 = np.zeros_like(v0)
    speed = float(np.hypot(u0, v0).mean())

    rng = np.random.default_rng(seed)
    members_fields = [[] for _ in range(members)]
    base = mosaics[-1]
    for step in range(steps):
        for m in range(members):
            k = 0.08 * (m - (members - 1) / 2) + rng.normal(0, 0.02)
            u = u0 * (1 + k)
            v = v0 * (1 + k)
            src = members_fields[m][-1] if members_fields[m] else base
            field = advect(src, u, v)
            field = apply_correction(field, u, v, w)
            decay = 1.0 - 0.004 * (step + 1)
            field = np.where(field < 6.0, 0.0, field * decay)
            members_fields[m].append(field.astype(np.float32))

    stack = np.stack([np.stack(m, axis=0) for m in members_fields], axis=0)
    mean = stack.mean(axis=0)
    prob30 = (stack >= 30.0).mean(axis=0)
    prob45 = (stack >= 45.0).mean(axis=0)
    return {
        "frames": mean,
        "prob30": prob30,
        "prob45": prob45,
        "flow": (u0, v0),
        "speed_px": speed,
        "correction": w,
        "members": members,
    }


def skill(persistence: np.ndarray, forecasted: np.ndarray, truth: np.ndarray) -> dict:
    mask = np.isfinite(truth) & np.isfinite(persistence) & np.isfinite(forecasted) & (truth > 5.0)
    if mask.sum() < 100:
        return {"n": int(mask.sum())}
    p_err = np.abs(persistence[mask] - truth[mask])
    f_err = np.abs(forecasted[mask] - truth[mask])
    return {
        "n": int(mask.sum()),
        "persistence_mae": float(p_err.mean()),
        "advection_mae": float(f_err.mean()),
        "improvement_pct": float(100.0 * (1 - f_err.mean() / max(1e-6, p_err.mean()))),
    }
