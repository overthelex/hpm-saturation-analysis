"""Reusable parallel map over the simulator (all CPU cores).

The simulator is deterministic and each run is independent, so evaluation is embarrassingly
parallel. Worker functions MUST be top-level (picklable) to run under ProcessPoolExecutor.
"""
import os
from concurrent.futures import ProcessPoolExecutor


def pmap(fn, items, workers=None, chunksize=1):
    """Apply fn to each item across `workers` processes (default: all cores). Order preserved."""
    workers = workers or os.cpu_count()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(fn, items, chunksize=chunksize))
