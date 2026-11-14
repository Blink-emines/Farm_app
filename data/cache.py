"""Disk cache for raw API responses. Key = endpoint + sorted query parameters."""
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
    path = _path(endpoint, params)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except ValueError:
        return None  # damaged file: treat as a miss


def cached_get(endpoint, params, fetcher):
    """Return the cached response, or call fetcher(url) once and store the result.

    fetcher raises on failure, and failures are never cached."""
    hit = lookup(endpoint, params)
    if hit is not None:
        return Cached(hit["response"], hit["fetched_at"], "cache")
    url = endpoint + "?" + "&".join(f"{k}={v}" for k, v in _sorted_params(params))
    response = fetcher(url)
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _path(endpoint, params).write_text(json.dumps({
        "endpoint": endpoint, "params": _sorted_params(params),
        "fetched_at": fetched_at, "response": response,
    }))
    return Cached(response, fetched_at, "live")
