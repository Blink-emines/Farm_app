"""Disk cache for raw API responses. Key = endpoint + sorted query parameters."""
import gzip
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

CACHE_DIR = Path(__file__).parent / "cache"


class Cached(NamedTuple):
    response: dict
    fetched_at: str
    status: str  # "live" (fetched now) or "cache" (stored earlier)


def _sorted_params(params):
    return sorted((str(k), str(v)) for k, v in params)


def _path(endpoint, params):
    params = _sorted_params(params)
    key = endpoint + "?" + "&".join(f"{k}={v}" for k, v in params)
    digest = hashlib.sha256(key.encode()).hexdigest()[:16]
    d = dict(params)
    lat = d.get("latitude", d.get("lat", "x"))
    lon = d.get("longitude", d.get("lon", "x"))
    host = endpoint.split("//")[-1].split("/")[0].split(".")[0]
    return CACHE_DIR / f"{host}_{lat}_{lon}_{digest}.json"


def lookup(endpoint, params):
    """Return the saved entry (plain .json or compressed .json.gz), or None."""
    path = _path(endpoint, params)
    for candidate in (path, path.with_name(path.name + ".gz")):
        if candidate.exists():
            try:
                opener = gzip.open if candidate.suffix == ".gz" else open
                with opener(candidate, "rt", encoding="utf-8") as f:
                    return json.load(f)
            except (ValueError, OSError):
                return None  # damaged file: treat as a miss
    return None


def cached_get(endpoint, params, fetcher, compress=False):
    """Return the cached response, or call fetcher(url) once and store the result.

    fetcher raises on failure, and failures are never cached. compress=True stores .json.gz
    (used for the large NASA POWER responses)."""
    hit = lookup(endpoint, params)
    if hit is not None:
        return Cached(hit["response"], hit["fetched_at"], "cache")
    url = endpoint + "?" + "&".join(f"{k}={v}" for k, v in _sorted_params(params))
    response = fetcher(url)
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    entry = json.dumps({"endpoint": endpoint, "params": _sorted_params(params),
                        "fetched_at": fetched_at, "response": response})
    path = _path(endpoint, params)
    if compress:
        path = path.with_name(path.name + ".gz")
        tmp = path.with_name(path.name + ".part")
        with gzip.open(tmp, "wt", encoding="utf-8") as f:
            f.write(entry)
        tmp.replace(path)  # a half-written file is never seen as a cache hit
    else:
        path.write_text(entry)
    return Cached(response, fetched_at, "live")
