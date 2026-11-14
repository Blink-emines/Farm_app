"""Input checks: query coordinates and the StrategyRequest JSON schema."""
import json
import math

from django.conf import settings
from jsonschema import Draft202012Validator

_validator = None


def request_validator():
    global _validator
    if _validator is None:
        path = settings.BASE_DIR.parent / 'docs' / 'contracts' / 'strategy.schema.json'
        with open(path, encoding='utf-8') as f:
            defs = json.load(f)['$defs']
        _validator = Draft202012Validator({'$ref': '#/$defs/StrategyRequest', '$defs': defs})
    return _validator


def first_request_problem(body):
    """Return a plain message for the first problem in body, or None if valid."""
    err = next(iter(request_validator().iter_errors(body)), None)
    if err is None:
        return None
    where = '.'.join(str(p) for p in err.absolute_path) or 'request'
    return f'{where}: {err.message}'


def parse_coordinates(params):
    """Return (lat, lon) from query params, or None if missing or not valid."""
    try:
        lat = float(params['lat'])
        lon = float(params['lon'])
    except (KeyError, ValueError):
        return None
    if not (math.isfinite(lat) and math.isfinite(lon)):
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return lat, lon
