from datetime import datetime, timedelta, timezone

import numpy as np

from radar.grid import Grid
from radar.sources import imerg

G = Grid()

candidates = [
    datetime(2025, 1, 10, 12, tzinfo=timezone.utc),
    datetime(2025, 1, 15, 12, tzinfo=timezone.utc),
    datetime(2025, 1, 20, 12, tzinfo=timezone.utc),
    datetime(2025, 2, 1, 12, tzinfo=timezone.utc),
    datetime(2025, 2, 10, 12, tzinfo=timezone.utc),
    datetime(2025, 2, 20, 12, tzinfo=timezone.utc),
    datetime(2025, 1, 25, 12, tzinfo=timezone.utc),
    datetime(2025, 12, 25, 12, tzinfo=timezone.utc),
]

for start in candidates:
    covs = []
    for i in range(6):
        when = start - timedelta(minutes=30 * (11 - i))
        try:
            f = imerg.fetch_field(G, when)
            finite = int(np.isfinite(f).sum())
            total = G.lat2d.size
            covs.append(100.0 * finite / total)
        except Exception as e:
            covs.append(-1)
    print(start.date(), "coverage% (последние 6 кадров):", [round(c, 2) for c in covs])