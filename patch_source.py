import pathlib
p = pathlib.Path("radar/sources/netcdf_source.py")
s = p.read_text(encoding="utf-8")
s = s.replace('''def read_volume(path: Path) -> dict:''', '''def _attr(ds, name, default=None):
    value = getattr(ds, name, default)
    if isinstance(value, bytes):
        value = value.decode("utf-8", "replace").strip("\\x00")
    if isinstance(value, tuple) and value and isinstance(value[0], bytes):
        value = value[0].decode("utf-8", "replace").strip("\\x00")
    return value


def read_volume(path: Path) -> dict:''')
s = s.replace('getattr(ds, "station_id", path.stem.split("_")[0])', '_attr(ds, "station_id", path.stem.split("_")[0])')
s = s.replace('getattr(ds, "station_name", "")', '_attr(ds, "station_name", "")')
s = s.replace('getattr(ds, "latitude", 0.0)', '_attr(ds, "latitude", 0.0)')
s = s.replace('getattr(ds, "longitude", 0.0)', '_attr(ds, "longitude", 0.0)')
s = s.replace('getattr(ds, "range_km", 250.0)', '_attr(ds, "range_km", 250.0)')
p.write_text(s, encoding="utf-8")
print("patched")
