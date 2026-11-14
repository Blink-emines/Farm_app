"""Download the SoilGrids 2.0 rasters for the Morocco box from ISRIC's official WCS.

Usage (from the repository root):  backend/.venv/bin/python -m data.download_soil
15 layers: clay, sand, silt, soc, phh2o x 0-5, 5-15, 15-30 cm, statistic "mean", 250 m, native
Interrupted Goode Homolosine grid (EPSG:152160). Files already downloaded are skipped, so the
script can be re-run after an interruption. Rasters are gitignored; this script is the record."""
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from rasterio.warp import transform_bounds

from . import region, soil_raster

WCS = "https://maps.isric.org/mapserv"
CRS_URI = "http://www.opengis.net/def/crs/EPSG/0/152160"


def bbox_igh():
    left, bottom, right, top = transform_bounds(
        "EPSG:4326", soil_raster.IGH, region.LON_MIN, region.LAT_MIN, region.LON_MAX, region.LAT_MAX,
        densify_pts=100)
    # snap outward to the 250 m grid
    return (int(left // 250) * 250, int(bottom // 250) * 250, int(-(-right // 250)) * 250, int(-(-top // 250)) * 250)


def url(prop, depth, box):
    left, bottom, right, top = box
    query = [("map", f"/map/{prop}.map"), ("SERVICE", "WCS"), ("VERSION", "2.0.1"), ("REQUEST", "GetCoverage"),
             ("COVERAGEID", f"{prop}_{depth}_mean"), ("FORMAT", "image/tiff"),
             ("SUBSET", f"x({left},{right})"), ("SUBSET", f"y({bottom},{top})"), ("SUBSETTINGCRS", CRS_URI)]
    return WCS + "?" + urllib.parse.urlencode(query)


def download(prop, depth, box, attempts=4):
    target = soil_raster.layer_path(prop, depth)
    tmp = target.with_name(target.name + ".part")
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(url(prop, depth, box), timeout=600) as resp, open(tmp, "wb") as out:
                while chunk := resp.read(1 << 20):
                    out.write(chunk)
            if tmp.stat().st_size < 10_000:
                raise OSError("response too small, probably an error message")
            tmp.replace(target)
            return
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            print(f"  {prop} {depth}: attempt {attempt} failed: {exc}", flush=True)
            time.sleep(10 * attempt)
    raise SystemExit(f"giving up on {prop} {depth}")


def fetch_layer(job):
    prop, depth, box = job
    target = soil_raster.layer_path(prop, depth)
    if target.exists():
        print(f"{prop} {depth}: already downloaded", flush=True)
        return
    t = time.time()
    download(prop, depth, box)
    print(f"{prop} {depth}: {target.stat().st_size / 1e6:.0f} MB in {time.time() - t:.0f}s", flush=True)


def main(workers=3):
    soil_raster.RASTER_DIR.mkdir(exist_ok=True)
    box = bbox_igh()
    started = time.time()
    jobs = [(p, d, box) for p in soil_raster.PROPERTIES for d in soil_raster.DEPTHS]
    with ThreadPoolExecutor(max_workers=workers) as pool:   # a few at a time: the service is shared
        list(pool.map(fetch_layer, jobs))
    (soil_raster.RASTER_DIR / "manifest.json").write_text(json.dumps({
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "service": WCS, "crs": CRS_URI, "bbox_igh": box,
        "region_box": [region.LAT_MIN, region.LAT_MAX, region.LON_MIN, region.LON_MAX]}, indent=1))
    total = sum(p.stat().st_size for p in soil_raster.RASTER_DIR.glob("*.tif"))
    print(f"done: {total / 1e6:.0f} MB in {time.time() - started:.0f}s", flush=True)


if __name__ == "__main__":
    main()
