"""Integration tests against the running Django API on http://localhost:8000.

Start the backend first (`backend/.venv/bin/python backend/manage.py runserver`).
If the server is not reachable, every test here is SKIPPED with that reason.
A skip is not a pass: these must run and pass before the project is reported
as verified.

Uses only the standard library (urllib), so no new dependency.
"""

import json
import urllib.error
import urllib.request

import pytest

from tests.conftest import PRIORITY_KEYS

API = "http://localhost:8000"
TIMEOUT = 60  # first call may fetch NASA POWER data and be slow

DEFAULT_REQUEST = {
    "latitude": 33.96,
    "longitude": -5.27,
    "current_rotation": {"seasons": [{"crop_id": "wheat"}, {"crop_id": "fallow"}]},
    "priorities": {k: 3 for k in PRIORITY_KEYS},
}


def _request(method, path, body=None):
    """Return (status, parsed_json_or_None). Never raises for HTTP errors."""
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(API + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        raw = err.read().decode("utf-8")
        try:
            return err.code, json.loads(raw)
        except json.JSONDecodeError:
            return err.code, None


@pytest.fixture(scope="module", autouse=True)
def require_server():
    try:
        urllib.request.urlopen(API + "/api/features?lat=33.96&lon=-5.27", timeout=TIMEOUT)
    except urllib.error.HTTPError:
        return  # server answers (any status) -> reachable
    except (urllib.error.URLError, OSError) as exc:
        pytest.skip(f"backend not reachable at {API}: {exc}")


def _assert_error_body(body, code):
    assert isinstance(body, dict) and set(body) == {"error"}, body
    assert body["error"]["code"] == code, body
    assert isinstance(body["error"]["message"], str) and body["error"]["message"], body


# ---------------------------------------------------------------------------
# GET /api/features
# ---------------------------------------------------------------------------

def test_features_default_point_returns_valid_features(features_validator):
    status, body = _request("GET", "/api/features?lat=33.96&lon=-5.27")
    assert status == 200, body
    errors = list(features_validator.iter_errors(body))
    assert not errors, [e.message for e in errors[:5]]


def test_features_invalid_coordinates_return_400():
    status, body = _request("GET", "/api/features?lat=abc&lon=-5.27")
    assert status == 400
    _assert_error_body(body, "invalid_coordinates")


def test_features_outside_pilot_region_returns_422():
    status, body = _request("GET", "/api/features?lat=48.85&lon=2.35")
    assert status == 422
    _assert_error_body(body, "outside_pilot_region")


# ---------------------------------------------------------------------------
# POST /api/strategies
# ---------------------------------------------------------------------------

def test_strategies_default_request_returns_valid_response(strategy_validator):
    status, body = _request("POST", "/api/strategies", DEFAULT_REQUEST)
    assert status == 200, body
    errors = list(strategy_validator.iter_errors(body))
    assert not errors, [e.message for e in errors[:5]]


def test_strategies_default_request_has_three_to_five_strategies_one_current():
    status, body = _request("POST", "/api/strategies", DEFAULT_REQUEST)
    assert status == 200, body
    assert 3 <= len(body["strategies"]) <= 5
    assert sum(1 for s in body["strategies"] if s["is_current"]) == 1


def test_strategies_invalid_body_returns_400_invalid_request():
    bad = {**DEFAULT_REQUEST, "priorities": {**DEFAULT_REQUEST["priorities"], "forage": 9}}
    status, body = _request("POST", "/api/strategies", bad)
    assert status == 400
    _assert_error_body(body, "invalid_request")


def test_strategies_outside_pilot_region_returns_422():
    far = {**DEFAULT_REQUEST, "latitude": 48.85, "longitude": 2.35}
    status, body = _request("POST", "/api/strategies", far)
    assert status == 422
    _assert_error_body(body, "outside_pilot_region")


def test_strategies_response_has_no_sentinel_values():
    status, body = _request("POST", "/api/strategies", DEFAULT_REQUEST)
    assert status == 200, body

    def walk(obj):
        if isinstance(obj, bool):
            return
        if isinstance(obj, (int, float)):
            assert obj > -999, obj
        elif isinstance(obj, dict):
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)

    walk(body)
