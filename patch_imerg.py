import pathlib
p = pathlib.Path("radar/sources/imerg.py")
s = p.read_text(encoding="utf-8")
s = s.replace('def _url(iso: str, z: int, x: int, y: int) -> str:', 'def _safe(iso: str) -> str:\n    return iso.replace(":", "")\n\n\ndef _url(iso: str, z: int, x: int, y: int) -> str:')
s = s.replace('probe = CACHE / "imerg" / iso / f"{ZOOM}_{x0}_{y0}.png"', 'probe = CACHE / "imerg" / _safe(iso) / f"{ZOOM}_{x0}_{y0}.png"')
s = s.replace('path = CACHE / "imerg" / iso / f"{ZOOM}_{tx}_{ty}.png"', 'path = CACHE / "imerg" / _safe(iso) / f"{ZOOM}_{tx}_{ty}.png"')
p.write_text(s, encoding="utf-8")
print("ok")
