from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image

from .colormap import colorize
from .config import LAT_MAX, LAT_MIN, LON_MAX, LON_MIN, TILE_ZOOMS
from .grid import Grid


def lonlat_to_world(lat: float, lon: float, z: int) -> tuple[float, float]:
    n = 256 * (2**z)
    x = (lon + 180.0) / 360.0 * n
    lat_r = math.radians(lat)
    y = (1.0 - math.log(math.tan(lat_r) + 1.0 / math.cos(lat_r)) / math.pi) / 2.0 * n
    return x, y


def tile_range(z: int) -> tuple[int, int, int, int]:
    x0, y0 = lonlat_to_world(LAT_MAX, LON_MIN, z)
    x1, y1 = lonlat_to_world(LAT_MIN, LON_MAX, z)
    return int(x0 // 256), int(x1 // 256), int(y0 // 256), int(y1 // 256)


def _lat_from_world_y(y: np.ndarray, n: float) -> np.ndarray:
    return np.degrees(np.arctan(np.sinh(np.pi * (1.0 - 2.0 * y / n))))


def render_zoom(grid: Grid, field: np.ndarray, z: int) -> tuple[Image.Image, tuple[int, int]]:
    tx0, tx1, ty0, ty1 = tile_range(z)
    nx = (tx1 - tx0 + 1) * 256
    ny = (ty1 - ty0 + 1) * 256
    n = 256 * (2**z)

    lons = ((np.arange(nx) + tx0 * 256 + 0.5) / n) * 360.0 - 180.0
    canvas = np.zeros((ny, nx, 4), dtype=np.uint8)
    block = 128
    for r0 in range(0, ny, block):
        r1 = min(ny, r0 + block)
        ys = np.arange(r0, r1) + ty0 * 256 + 0.5
        lats = _lat_from_world_y(ys, n)
        lon2d, lat2d = np.meshgrid(lons, lats)
        sampled = grid.sample(field, lat2d, lon2d)
        canvas[r0:r1] = colorize(sampled)
    return Image.fromarray(canvas, "RGBA"), (tx0, ty0)


def save_tiles(img: Image.Image, z: int, origin: tuple[int, int], out_dir: Path) -> int:
    tx0, ty0 = origin
    count = 0
    for iy in range(img.height // 256):
        for ix in range(img.width // 256):
            tile = img.crop((ix * 256, iy * 256, ix * 256 + 256, iy * 256 + 256))
            x = tx0 + ix
            y = ty0 + iy
            (out_dir / str(x)).mkdir(parents=True, exist_ok=True)
            tile.quantize(colors=48, method=Image.FASTOCTREE).save(out_dir / str(x) / f"{y}.png", compress_level=6)
            count += 1
    return count


def render_all_zooms(grid: Grid, field: np.ndarray, root: Path) -> dict:
    result = {}
    for z in TILE_ZOOMS:
        img, origin = render_zoom(grid, field, z)
        count = save_tiles(img, z, origin, root / str(z))
        result[z] = {"tiles": count, "origin": origin, "size": img.size}
    return result
