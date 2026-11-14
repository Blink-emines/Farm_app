"""Point lookup in the local SoilGrids rasters (downloaded once with data/download_soil.py).

One GeoTIFF per property and depth (15 files), 250 m, Interrupted Goode Homolosine, int16.
The WCS marks sea and other no-data pixels with 0 (no nodata flag is set in the file)."""
import json
from functools import lru_cache
from pathlib import Path

import rasterio
from rasterio.warp import transform

RASTER_DIR = Path(__file__).parent / "soil_rasters"
IGH = "+proj=igh +lat_0=0 +lon_0=0 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
DEPTHS = ("0-5cm", "5-15cm", "15-30cm")
# SoilGrids name -> contract field. Mapped units (g/kg, g/kg, g/kg, dg/kg, pH*10) all have
# d_factor 10 (verified on the REST service's unit_measure block), so value / 10 gives % / g/kg / pH.
PROPERTIES = {"clay": "clay_pct", "sand": "sand_pct", "silt": "silt_pct", "soc": "soc_g_kg", "phh2o": "ph_h2o"}
D_FACTOR = 10
SEARCH_RADIUS_PX = 12     # 3 km: nearest valid pixel for towns (SoilGrids masks built-up areas), dams, coast


class NoLandPixel(Exception):
    """No SoilGrids pixel with data at or near the point (sea or outside the rasters)."""


def layer_path(prop, depth):
    return RASTER_DIR / f"{prop}_{depth}.tif"


def available():
    return (RASTER_DIR / "manifest.json").exists() and all(
        layer_path(p, d).exists() for p in PROPERTIES for d in DEPTHS)


def fetched_at():
    try:
        return json.loads((RASTER_DIR / "manifest.json").read_text())["fetched_at"]
    except (OSError, ValueError, KeyError):
        return None


@lru_cache(maxsize=64)
def _open(path):
    return rasterio.open(path)


def lookup(latitude, longitude):
    """Return (layers, used_nearest_pixel). Raises NoLandPixel."""
    first = _open(str(layer_path("clay", DEPTHS[0])))
    xs, ys = transform("EPSG:4326", IGH, [longitude], [latitude])
    row, col = first.index(xs[0], ys[0])
    if not (0 <= row < first.height and 0 <= col < first.width):
        raise NoLandPixel("point is outside the soil rasters")
    r = SEARCH_RADIUS_PX
    r0, c0 = max(row - r, 0), max(col - r, 0)
    window = first.read(1, window=((r0, min(row + r + 1, first.height)), (c0, min(col + r + 1, first.width))))
    valid = [(abs(i + r0 - row) ** 2 + abs(j + c0 - col) ** 2, i + r0, j + c0)
             for i in range(window.shape[0]) for j in range(window.shape[1]) if window[i, j] > 0]
    if not valid:
        raise NoLandPixel("no SoilGrids land pixel at this point")
    _, prow, pcol = min(valid)
    layers = []
    for depth in DEPTHS:
        layer = {"depth": depth}
        for prop, field in PROPERTIES.items():
            ds = _open(str(layer_path(prop, depth)))
            raw = int(ds.read(1, window=((prow, prow + 1), (pcol, pcol + 1)))[0, 0])
            layer[field] = round(raw / D_FACTOR, 2) if raw > 0 else None
        layers.append(layer)
    return layers, (prow, pcol) != (row, col)
