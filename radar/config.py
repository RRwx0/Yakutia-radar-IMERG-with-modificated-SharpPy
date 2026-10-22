from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CLIENT = ROOT / "client"
VOLUMES = DATA / "volumes"
TILES = CLIENT / "tiles"
PROBE = DATA / "probe"
CACHE = DATA / "cache"

LON_MIN, LON_MAX = 104.0, 166.0
LAT_MIN, LAT_MAX = 54.0, 74.0
STEP = 0.03

OBS_FRAMES = 12
FRAME_MINUTES = 30
NOWCAST_STEPS = 4
DBZ_FLOOR = 5.0
DBZ_CEIL = 70.0
TILE_ZOOMS = (3, 4, 5, 6)
SOURCE = "imerg"
MAX_ZOOM = 6


@dataclass(frozen=True)
class Station:
    id: str
    name: str
    lat: float
    lon: float
    range_km: float = 250.0
    antenna_m: float = 120.0
    band: str = "C"
    beam_deg: float = 1.0
    gate_km: float = 1.0


STATIONS = (
    Station("yakutsk", "Якутск", 62.09, 129.77),
    Station("olekminsk", "Олёкминск", 60.37, 120.42),
)

TZ = timezone(timedelta(hours=9))


def frame_times(now: datetime | None = None) -> list[datetime]:
    now = now or datetime.now(timezone.utc)
    anchor = now.replace(second=0, microsecond=0)
    anchor -= timedelta(minutes=anchor.minute % FRAME_MINUTES)
    return [anchor - timedelta(minutes=FRAME_MINUTES * (OBS_FRAMES - 1 - i)) for i in range(OBS_FRAMES)]
