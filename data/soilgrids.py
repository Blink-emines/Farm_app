"""ISRIC SoilGrids point query: URL, fetch, unit conversion and fallback."""
import json
from pathlib import Path

from . import cache, http

ENDPOINT = "https://rest.isric.org/soilgrids/v2.0/properties/query"
FALLBACK_PATH = Path(__file__).parent / "fallback" / "saiss_soil.json"
DEPTHS = ("0-5cm", "5-15cm", "15-30cm")
# SoilGrids name -> (contract field, target unit SoilGrids must report)
PROPERTIES = {
    "clay": ("clay_pct", "%"), "sand": ("sand_pct", "%"), "silt": ("silt_pct", "%"),
    "soc": ("soc_g_kg", "g/kg"), "phh2o": ("ph_h2o", "-"),
}


class SoilParseError(Exception):
    """The SoilGrids response is not in the units or shape we expect."""


def _params(latitude, longitude):
    return ([("lat", f"{latitude:.2f}"), ("lon", f"{longitude:.2f}"), ("value", "mean")]
            + [("property", p) for p in PROPERTIES] + [("depth", d) for d in DEPTHS])


def build_url(latitude, longitude):
    # Keep the depth order as declared (a sorted URL would put 15-30cm first).
    return ENDPOINT + "?" + "&".join(f"{k}={v}" for k, v in _params(latitude, longitude))


def fetch(latitude, longitude):
    """Return cache.Cached (live or cache). Raises UpstreamUnavailable if the service fails."""
    return cache.cached_get(ENDPOINT, _params(latitude, longitude),
                            lambda url: http.fetch_json(url, timeout=60, retries=1))


def load_fallback():
    """Return (response, fetched_at) from the saved real response, or None if missing/damaged."""
    try:
        saved = json.loads(FALLBACK_PATH.read_text())
        return saved["response"], saved["fetched_at"]
    except (OSError, ValueError, KeyError):
        return None


def parse_layers(raw):
    """Convert a SoilGrids response to contract layers (%, g/kg, pH). null stays null."""
    try:
        by_depth = {d: {} for d in DEPTHS}
        for layer in raw["properties"]["layers"]:
            name = layer["name"]
            if name not in PROPERTIES:
                continue
            field, target = PROPERTIES[name]
            um = layer["unit_measure"]
            if um.get("target_units") != target:
                raise SoilParseError(f"{name}: target unit {um.get('target_units')!r}, expected {target!r}")
            factor = um["d_factor"]
            for depth in layer["depths"]:
                if depth["label"] in by_depth:
                    mean = depth["values"].get("mean")
                    by_depth[depth["label"]][field] = None if mean is None else round(mean / factor, 2)
    except (KeyError, TypeError, ZeroDivisionError) as exc:
        raise SoilParseError(f"unexpected SoilGrids shape: {exc!r}")
    layers = []
    for d in DEPTHS:
        values = by_depth[d]
        if values:
            layers.append({"depth": d, **{f: values.get(f) for f, _ in PROPERTIES.values()}})
    return layers
