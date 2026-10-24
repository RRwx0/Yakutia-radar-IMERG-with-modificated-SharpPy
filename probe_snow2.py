from datetime import datetime, timedelta, timezone

import numpy as np

from radar.grid import Grid
from radar.sources import imerg

G = Grid()

candidates = [
    datetime(2025, 1, 20, 12, tzinfo=timezone.utc),
    datetime(2025, 2, 10, 12, tzinfo=timezone.utc),
    datetime(2025, 2, 20, 12, tzinfo=timezone.utc),
    datetime(2025, 12, 25, 12, tzinfo=timezone.utc),
    datetime(2025, 1, 10, 12, tzinfo=timezone.utc),
]

for start in candidates:
    when = start - timedelta(minutes=30 * 3)
    f = imerg.fetch_field(G, when)
    cov = 100.0 * np.isfinite(f).sum() / G.lat2d.size
    print(start.date(), "coverage:", round(cov, 2), "%", "max:", round(float(np.nanmax(f)), 1) if np.isfinite(f).any() else None)