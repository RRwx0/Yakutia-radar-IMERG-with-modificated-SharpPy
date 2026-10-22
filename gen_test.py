import sys
import time
from datetime import datetime, timezone, timedelta

sys.path.insert(0, ".")

from radar.config import VOLUMES, frame_times
from radar.grid import Grid
from radar.sources import synthetic

if __name__ == "__main__":
    grid = Grid()
    times = frame_times()[-2:]
    t0 = time.time()
    meta = synthetic.generate_series(grid, times, VOLUMES)
    print("frames", len(meta), "seconds", round(time.time() - t0, 1))
    print(meta[0])
