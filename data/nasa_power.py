"""NASA POWER daily point API (community AG): grid cells, URL, fetch and parsing.

Verified by probing the live API (identical values inside a cell, a jump at its edge):
  - T2M, T2M_MAX, T2M_MIN, PRECTOTCORR, RH2M, WS2M, GWETROOT come from MERRA-2 cells
    0.5 deg latitude x 0.625 deg longitude, centres at multiples of 0.5 and 0.625.
    Cell edges are at latitude x.25 / x.75 and longitude (k + 0.5) * 0.625; a point exactly
    on an edge belongs to the cell to the north / east.
  - ALLSKY_SFC_SW_DWN comes from 1 x 1 degree cells (edges at whole degrees, centre at x.5).
Requests are made at the cell centre, so every point in a cell shares one cache entry."""
import numpy as np
import pandas as pd

from . import cache, http
from .errors import UpstreamUnavailable

ENDPOINT = "https://power.larc.nasa.gov/api/temporal/daily/point"
START_YEAR, END_YEAR = 2005, 2024

# Names and units verified against the parameters block of the POWER daily API response.
PARAMETERS = ("T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "RH2M", "WS2M", "ALLSKY_SFC_SW_DWN", "GWETROOT")
MERRA_PARAMETERS = tuple(p for p in PARAMETERS if p != "ALLSKY_SFC_SW_DWN")
RADIATION_PARAMETERS = ("ALLSKY_SFC_SW_DWN",)
EXPECTED_UNITS = {
    "T2M": "C", "T2M_MAX": "C", "T2M_MIN": "C", "PRECTOTCORR": "mm/day", "RH2M": "%",
    "WS2M": "m/s", "ALLSKY_SFC_SW_DWN": "MJ/m^2/day", "GWETROOT": "1",
}


def merra_cell_centre(latitude, longitude):
    """Centre (lat, lon) of the 0.5 x 0.625 degree cell holding a point (2-decimal inputs)."""
    lat_i = round(latitude * 100)             # hundredths of a degree
    lon_i = round(longitude * 10000)          # 1/10000 of a degree
    row = (lat_i - 25) // 50 + 1              # edges at .25 / .75, edge belongs to the north cell
    col = (lon_i + 3125) // 6250              # edges at (k + 0.5) * 0.625
    return round(row * 0.5, 3), round(col * 0.625, 3)


def radiation_cell_centre(latitude, longitude):
    """Centre (lat, lon) of the 1 x 1 degree cell holding a point."""
    return (round(latitude * 100) // 100) + 0.5, (round(longitude * 100) // 100) + 0.5


def _params(latitude, longitude, parameters):
    return [
        ("parameters", ",".join(parameters)), ("community", "AG"),
        ("latitude", f"{latitude:.3f}"), ("longitude", f"{longitude:.3f}"),
        ("start", f"{START_YEAR}0101"), ("end", f"{END_YEAR}1231"), ("format", "JSON"),
    ]


def build_url(latitude, longitude, parameters=PARAMETERS):
    return ENDPOINT + "?" + "&".join(f"{k}={v}" for k, v in sorted(_params(latitude, longitude, parameters)))


def cell_requests(latitude, longitude):
    """The two cache entries a point needs: (centre lat, centre lon, parameters) each."""
    return [(*merra_cell_centre(latitude, longitude), MERRA_PARAMETERS),
            (*radiation_cell_centre(latitude, longitude), RADIATION_PARAMETERS)]


def fetch_cell(lat_c, lon_c, parameters):
    """Cached fetch of one cell. Returns cache.Cached."""
    return cache.cached_get(ENDPOINT, _params(lat_c, lon_c, parameters),
                            lambda url: http.fetch_json(url, timeout=120, retries=1), compress=True)


def fetch_daily(latitude, longitude):
    """Return (DataFrame, elevation_m or None, fetched_at, status)."""
    frames, elevation, stamps, statuses = [], None, [], []
    for lat_c, lon_c, parameters in cell_requests(latitude, longitude):
        got = fetch_cell(lat_c, lon_c, parameters)
        df, elev = parse_daily(got.response, parameters)
        frames.append(df)
        if parameters == MERRA_PARAMETERS:
            elevation = elev
        stamps.append(got.fetched_at)
        statuses.append(got.status)
    df = pd.concat(frames, axis=1)[list(PARAMETERS)]
    return df, elevation, min(stamps), "live" if "live" in statuses else "cache"


def parse_daily(raw, parameters=PARAMETERS):
    try:
        units = {k: v.get("units") for k, v in raw["parameters"].items()}
        for name in parameters:
            if units.get(name) != EXPECTED_UNITS[name]:
                raise UpstreamUnavailable(
                    f"NASA POWER reports {name} in '{units.get(name)}', expected '{EXPECTED_UNITS[name]}'.")
        fill = raw["header"].get("fill_value", -999.0)
        data = raw["properties"]["parameter"]
        df = pd.DataFrame({name: pd.Series(data[name]) for name in parameters})
        df.index = pd.to_datetime(df.index, format="%Y%m%d")
        df = df.sort_index().astype(float)
        df = df.where(df != fill, np.nan)
        coords = raw["geometry"]["coordinates"]
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise UpstreamUnavailable(f"NASA POWER response has an unexpected shape: {exc!r}")
    elevation = float(coords[2]) if len(coords) > 2 and coords[2] is not None and coords[2] != fill else None
    return df, elevation
