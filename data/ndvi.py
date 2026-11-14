"""NASA MODIS NDVI (MOD13Q1, 250 m, 16-day) via the ORNL DAAC MODIS web service. No API key.

The service is slow (about 50 s per request) and allows at most 10 dates per request, one band
per request. Fetching a point therefore takes many requests, so `warm()` fills the cache once
and `get_features` reads the cache only (unless FARM_NDVI_LIVE=1)."""
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import pandas as pd

from . import cache, http
from .errors import UpstreamUnavailable

ENDPOINT = "https://modis.ornl.gov/rst/api/v1/MOD13Q1/subset"
BASE_URL = "https://modis.ornl.gov/rst/api/v1/"
PRODUCT = "MODIS MOD13Q1 NDVI, 250 m, 16-day"
START_YEAR, END_YEAR = 2020, 2024
LIVE_FETCH = os.environ.get("FARM_NDVI_LIVE") == "1"

NDVI_BAND = "250m_16_days_NDVI"
RELIABILITY_BAND = "250m_16_days_pixel_reliability"
# Verified from the service's band list: scale 0.0001, valid range -2000..10000, fill -3000.
SCALE, FILL, VALID_MIN, VALID_MAX = 0.0001, -3000, -2000, 10000
GOOD_RELIABILITY = (0, 1)   # 0 good data, 1 marginal; 2 snow/ice, 3 cloudy and -1 fill are dropped
CHUNK = 10                  # service limit: 10 dates per request


class NdviUnavailable(Exception):
    """No usable NDVI (service failed, point not cached, or nothing valid)."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def modis_dates():
    """Composite start dates 'AYYYYDDD': 16-day steps from day 1, 23 per year."""
    return [f"A{y}{1 + 16 * k:03d}" for y in range(START_YEAR, END_YEAR + 1) for k in range(23)]


def chunks():
    d = modis_dates()
    return [(d[i], d[min(i + CHUNK, len(d)) - 1]) for i in range(0, len(d), CHUNK)]


def _params(latitude, longitude, band, start, end):
    return [("latitude", f"{latitude:.2f}"), ("longitude", f"{longitude:.2f}"), ("band", band),
            ("startDate", start), ("endDate", end), ("kmAboveBelow", "0"), ("kmLeftRight", "0")]


def _fetch(latitude, longitude, band, start, end, allow_network):
    params = _params(latitude, longitude, band, start, end)
    if not allow_network:
        hit = cache.lookup(ENDPOINT, params)
        if hit is None:
            raise NdviUnavailable("ndvi_not_cached",
                                  "NDVI for this point has not been downloaded yet (the satellite service is slow).")
        return cache.Cached(hit["response"], hit["fetched_at"], "cache")
    try:
        return cache.cached_get(ENDPOINT, params, lambda url: http.fetch_json(url, timeout=150, retries=3))
    except UpstreamUnavailable as exc:
        raise NdviUnavailable("ndvi_unavailable", f"The MODIS NDVI service did not answer: {exc}")


def parse_chunk(response):
    """{modis_date: (calendar_date, raw single-pixel value or None)}."""
    try:
        out = {}
        for item in response["subset"]:
            value = item["data"][0]
            out[item["modis_date"]] = (item["calendar_date"], value)
        return out
    except (KeyError, IndexError, TypeError) as exc:
        raise NdviUnavailable("ndvi_unavailable", f"Unexpected MODIS response shape: {exc!r}")


def clean_series(ndvi_raw, reliability_raw):
    """{calendar_date: NDVI} keeping only valid, good/marginal pixels, scaled by 0.0001."""
    out = {}
    for mdate, (cal, raw) in ndvi_raw.items():
        rel = reliability_raw.get(mdate, (None, None))[1]
        if raw is None or raw == FILL or not (VALID_MIN <= raw <= VALID_MAX):
            continue
        if rel not in GOOD_RELIABILITY:
            continue
        out[cal] = raw * SCALE
    return out


def monthly_values(series):
    """Return (ndvi_monthly over the period, recent) from {calendar_date: NDVI}.

    A composite counts for the month of its mid-point (start date + 8 days)."""
    rows = []
    for cal, v in series.items():
        mid = date.fromisoformat(cal) + timedelta(days=8)
        rows.append((mid.year, mid.month, v))
    if not rows:
        raise NdviUnavailable("ndvi_unavailable", "No valid NDVI values (all cloudy or missing).")
    df = pd.DataFrame(rows, columns=["year", "month", "ndvi"])
    per_ym = df.groupby(["year", "month"])["ndvi"].mean()

    def as_list(s):
        s = s.reindex(range(1, 13))
        return [None if pd.isna(v) else round(float(v), 3) for v in s]

    period_mean = as_list(per_ym.groupby(level="month").mean())
    recent_year = END_YEAR
    recent = per_ym.xs(recent_year, level="year") if recent_year in per_ym.index.get_level_values("year") else pd.Series(dtype=float)
    return period_mean, {"year": recent_year, "values": as_list(recent)}


def load(latitude, longitude, allow_network=None):
    """Return a dict {status, fetched_at, ndvi_monthly, recent}. Raises NdviUnavailable.

    status is 'live' if any request was fetched now, otherwise 'cache'."""
    allow_network = LIVE_FETCH if allow_network is None else allow_network
    raw = {NDVI_BAND: {}, RELIABILITY_BAND: {}}
    statuses, stamps = [], []
    for start, end in chunks():
        for band in (NDVI_BAND, RELIABILITY_BAND):
            got = _fetch(latitude, longitude, band, start, end, allow_network)
            raw[band].update(parse_chunk(got.response))
            statuses.append(got.status)
            stamps.append(got.fetched_at)
    period_mean, recent = monthly_values(clean_series(raw[NDVI_BAND], raw[RELIABILITY_BAND]))
    return {"status": "live" if "live" in statuses else "cache", "fetched_at": max(stamps),
            "ndvi_monthly": period_mean, "recent": recent}


def warm(latitude, longitude, workers=3, log=print):
    """Download and cache every request for a point (slow: run once, outside the web request)."""
    jobs = [(b, s, e) for s, e in chunks() for b in (NDVI_BAND, RELIABILITY_BAND)]

    def one(job):
        band, start, end = job
        t = time.time()
        _fetch(latitude, longitude, band, start, end, allow_network=True)
        log(f"{band} {start}..{end} ok in {time.time() - t:.0f}s")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(one, jobs))


if __name__ == "__main__":
    import sys
    warm(float(sys.argv[1]), float(sys.argv[2]))
