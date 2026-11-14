"""NASA POWER daily point API (community AG): URL, fetch and parsing."""
import numpy as np
import pandas as pd

from . import cache, http
from .errors import UpstreamUnavailable

ENDPOINT = "https://power.larc.nasa.gov/api/temporal/daily/point"
START_YEAR, END_YEAR = 2005, 2024

# Names and units verified against the parameters block of the POWER daily API response.
PARAMETERS = ("T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "RH2M", "WS2M", "ALLSKY_SFC_SW_DWN", "GWETROOT")
EXPECTED_UNITS = {
    "T2M": "C", "T2M_MAX": "C", "T2M_MIN": "C", "PRECTOTCORR": "mm/day", "RH2M": "%",
    "WS2M": "m/s", "ALLSKY_SFC_SW_DWN": "MJ/m^2/day", "GWETROOT": "1",
}


def _params(latitude, longitude):
    return [
        ("parameters", ",".join(PARAMETERS)), ("community", "AG"),
        ("latitude", f"{latitude:.2f}"), ("longitude", f"{longitude:.2f}"),
        ("start", f"{START_YEAR}0101"), ("end", f"{END_YEAR}1231"), ("format", "JSON"),
    ]


def build_url(latitude, longitude):
    return ENDPOINT + "?" + "&".join(f"{k}={v}" for k, v in sorted(_params(latitude, longitude)))


def fetch_daily(latitude, longitude):
    """Return (DataFrame, elevation_m or None, fetched_at, status)."""
    got = cache.cached_get(ENDPOINT, _params(latitude, longitude),
                           lambda url: http.fetch_json(url, timeout=120, retries=1))
    df, elevation = parse_daily(got.response)
    return df, elevation, got.fetched_at, got.status


def parse_daily(raw):
    try:
        units = {k: v.get("units") for k, v in raw["parameters"].items()}
        for name, unit in EXPECTED_UNITS.items():
            if units.get(name) != unit:
                raise UpstreamUnavailable(
                    f"NASA POWER reports {name} in '{units.get(name)}', expected '{unit}'.")
        fill = raw["header"].get("fill_value", -999.0)
        data = raw["properties"]["parameter"]
        df = pd.DataFrame({name: pd.Series(data[name]) for name in PARAMETERS})
        df.index = pd.to_datetime(df.index, format="%Y%m%d")
        df = df.sort_index().astype(float)
        df = df.where(df != fill, np.nan)
        coords = raw["geometry"]["coordinates"]
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise UpstreamUnavailable(f"NASA POWER response has an unexpected shape: {exc!r}")
    elevation = float(coords[2]) if len(coords) > 2 and coords[2] is not None and coords[2] != fill else None
    return df, elevation
