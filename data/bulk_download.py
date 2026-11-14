"""Download NASA POWER daily data for every grid cell that touches Moroccan land.

Usage (from the repository root, after data.download_soil has finished):
    backend/.venv/bin/python -m data.bulk_download [--dry-run] [--limit N]

Land comes from the SoilGrids clay raster (no sea pixels), not from a political boundary.
Each cell is requested once at its centre and stored in data/cache/ (gzip); cells already in the
cache are skipped, so the script is resumable. Sequential with a pause between requests."""
import argparse
import sys
import time

import numpy as np
import rasterio
from rasterio.warp import transform

from . import cache, nasa_power, region, soil_raster
from .errors import UpstreamUnavailable

BLOCK = 8          # land test at 8 x 250 m = 2 km blocks (a block is land if any pixel in it is)
PAUSE_S = 0.5      # politeness delay after every live request
ATTEMPTS = 3


def land_cells():
    """Return (merra_cells, radiation_cells): sorted lists of (lat_c, lon_c) touching land in the box."""
    path = soil_raster.layer_path("clay", soil_raster.DEPTHS[0])
    rows, cols = [], []
    with rasterio.open(path) as ds:
        t = ds.transform
        width = ds.width // BLOCK * BLOCK
        step = BLOCK * 100                      # read 100 block-rows at a time
        for r0 in range(0, ds.height // BLOCK * BLOCK, step):
            h = min(step, ds.height // BLOCK * BLOCK - r0)
            strip = ds.read(1, window=((r0, r0 + h), (0, width)))
            land = (strip.reshape(h // BLOCK, BLOCK, width // BLOCK, BLOCK) > 0).any(axis=(1, 3))
            br, bc = np.nonzero(land)
            rows.append(br + r0 // BLOCK)
            cols.append(bc)
    rows, cols = np.concatenate(rows), np.concatenate(cols)
    xs = t.c + (cols + 0.5) * t.a * BLOCK
    ys = t.f + (rows + 0.5) * t.e * BLOCK
    lons, lats = transform(soil_raster.IGH, "EPSG:4326", xs.tolist(), ys.tolist())
    merra, radiation = set(), set()
    for lat, lon in zip(lats, lons):
        lat, lon = round(lat, 2), round(lon, 2)
        if region.LAT_MIN <= lat <= region.LAT_MAX and region.LON_MIN <= lon <= region.LON_MAX:
            merra.add(nasa_power.merra_cell_centre(lat, lon))
            radiation.add(nasa_power.radiation_cell_centre(lat, lon))
    return sorted(merra), sorted(radiation)


def jobs():
    merra, radiation = land_cells()
    return ([(lat, lon, nasa_power.MERRA_PARAMETERS) for lat, lon in merra]
            + [(lat, lon, nasa_power.RADIATION_PARAMETERS) for lat, lon in radiation])


def is_cached(job):
    lat, lon, params = job
    return cache.lookup(nasa_power.ENDPOINT, nasa_power._params(lat, lon, params)) is not None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="only count the cells")
    ap.add_argument("--limit", type=int, default=None, help="stop after this many live downloads")
    args = ap.parse_args(argv)

    todo_all = jobs()
    todo = [j for j in todo_all if not is_cached(j)]
    print(f"{len(todo_all)} cells touch land ({sum(j[2] == nasa_power.MERRA_PARAMETERS for j in todo_all)} "
          f"MERRA-2, {sum(j[2] == nasa_power.RADIATION_PARAMETERS for j in todo_all)} radiation); "
          f"{len(todo_all) - len(todo)} already cached, {len(todo)} to download", flush=True)
    if args.dry_run:
        return 0
    started, done, failed = time.time(), 0, []
    for job in todo:
        if args.limit is not None and done >= args.limit:
            break
        lat, lon, params = job
        for attempt in range(1, ATTEMPTS + 1):
            try:
                nasa_power.fetch_cell(lat, lon, params)
                done += 1
                break
            except UpstreamUnavailable as exc:
                print(f"  cell {lat},{lon} attempt {attempt} failed: {exc}", flush=True)
                time.sleep(5 * attempt)
        else:
            failed.append(job)
        if done and done % 10 == 0:
            rate = (time.time() - started) / done
            print(f"{done}/{len(todo)} downloaded, {rate:.1f} s each, about {rate * (len(todo) - done) / 60:.0f} min left",
                  flush=True)
        time.sleep(PAUSE_S)
    print(f"finished: {done} downloaded, {len(failed)} failed, {time.time() - started:.0f}s", flush=True)
    for lat, lon, params in failed:
        print(f"  FAILED {lat},{lon} {params[0]}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
