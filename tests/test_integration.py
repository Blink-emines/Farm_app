"""Integration checks on the running API (http://localhost:8000).

Needs the backend running. If it is not reachable, every test here is
SKIPPED with that reason; a skip is not a pass.

Request under test: wheat then fallow, no months sent (the engine fills
typical Saïss months), default point 33.96, -5.27.
"""

import urllib.error
import urllib.request

import pytest

from tests.conftest import PRIORITY_KEYS
from tests.test_api import API, TIMEOUT, _request

WHEAT_FALLOW = {
    "latitude": 33.96,
    "longitude": -5.27,
    "current_rotation": {"seasons": [{"crop_id": "wheat"}, {"crop_id": "fallow"}]},
    "priorities": {k: 3 for k in PRIORITY_KEYS},
}

WHEAT_FALLOW_WITH_MONTHS = {
    **WHEAT_FALLOW,
    "current_rotation": {
        "seasons": [
            {"crop_id": "wheat", "sow_month": 11, "harvest_month": 6},
            {"crop_id": "fallow", "sow_month": 7, "harvest_month": 6},
        ]
    },
}

MONTHS_TOTAL = 12


@pytest.fixture(scope="module", autouse=True)
def require_server():
    try:
        urllib.request.urlopen(API + "/api/features?lat=33.96&lon=-5.27", timeout=TIMEOUT)
    except urllib.error.HTTPError:
        return
    except (urllib.error.URLError, OSError) as exc:
        pytest.skip(f"backend not reachable at {API}: {exc}")


@pytest.fixture(scope="module")
def wheat_fallow():
    status, body = _request("POST", "/api/strategies", WHEAT_FALLOW)
    assert status == 200, body
    return body


@pytest.fixture(scope="module")
def wheat_fallow_with_months():
    status, body = _request("POST", "/api/strategies", WHEAT_FALLOW_WITH_MONTHS)
    assert status == 200, body
    return body


def _gap_codes(strategy):
    return [m["code"] for m in strategy["information_gaps"]]


# ---------------------------------------------------------------------------
# Current rotation and strategy shape
# ---------------------------------------------------------------------------

def test_wheat_fallow_returns_exactly_one_current(wheat_fallow):
    current = [s for s in wheat_fallow["strategies"] if s["is_current"]]
    assert len(current) == 1, [s["id"] for s in current]


def test_every_strategy_has_at_least_one_why_entry(wheat_fallow):
    for s in wheat_fallow["strategies"]:
        assert len(s["why"]) >= 1, s["id"]


def test_every_strategy_has_at_least_one_risk(wheat_fallow):
    for s in wheat_fallow["strategies"]:
        assert len(s["risks_for_local_review"]) >= 1, s["id"]


# ---------------------------------------------------------------------------
# Seasons do not overlap; calendar agrees with the seasons
# ---------------------------------------------------------------------------

def _occupancy(seasons):
    """Map cycle index (0..12n-1) -> crop_id, for the whole repeating rotation.
    Season k starts at month index 12*k + (sow - 1) and lasts until harvest,
    possibly running into the next year. Raises AssertionError when two
    seasons claim the same month."""
    cycle = MONTHS_TOTAL * len(seasons)
    owner = {}
    for k, season in enumerate(seasons):
        sow = season["sow_month"] - 1
        duration = (season["harvest_month"] - 1 - sow) % MONTHS_TOTAL + 1
        for t in range(duration):
            index = (MONTHS_TOTAL * k + sow + t) % cycle
            assert index not in owner, (
                f"seasons overlap: {season['crop_id']} and {owner[index]} both claim cycle month {index}"
            )
            owner[index] = season["crop_id"]
    return owner, cycle


def test_no_two_seasons_overlap_in_any_strategy(wheat_fallow):
    for s in wheat_fallow["strategies"]:
        _occupancy(s["seasons"])  # raises on overlap


def test_calendar_rows_match_the_season_windows(wheat_fallow):
    for s in wheat_fallow["strategies"]:
        owner, cycle = _occupancy(s["seasons"])
        assert len(s["calendar"]) == len(s["seasons"]), s["id"]
        # Rows are farming years starting at the first sowing month (e.g. November to October).
        t0 = s["seasons"][0]["sow_month"] - 1
        for row in s["calendar"]:
            assert row["months"][0]["month"] == t0 + 1, s["id"]
            for month in row["months"]:
                index = (t0 + MONTHS_TOTAL * (row["year"] - 1) + (month["month"] - 1 - t0) % MONTHS_TOTAL) % cycle
                expected = owner.get(index)
                assert month["crop_id"] == expected, (
                    f"{s['id']} year {row['year']} month {month['month']}: "
                    f"calendar says {month['crop_id']}, seasons say {expected}"
                )


# ---------------------------------------------------------------------------
# Data gaps and missing months
# ---------------------------------------------------------------------------

def test_features_summary_data_gaps_match_features_endpoint(wheat_fallow):
    status, features = _request("GET", "/api/features?lat=33.96&lon=-5.27")
    assert status == 200, features
    expected = [g["code"] for g in features["data_gaps"]]
    assert wheat_fallow["features_summary"]["data_gaps"] == expected


def test_default_months_gap_present_and_confidence_low_when_no_months_sent(wheat_fallow):
    current = next(s for s in wheat_fallow["strategies"] if s["is_current"])
    assert "gap_default_months" in _gap_codes(current), _gap_codes(current)
    assert current["confidence"] == "low", current["confidence"]


def test_every_strategy_with_default_months_gap_has_low_confidence(wheat_fallow):
    for s in wheat_fallow["strategies"]:
        if "gap_default_months" in _gap_codes(s):
            assert s["confidence"] == "low", s["id"]


def test_default_months_gap_absent_when_months_are_sent(wheat_fallow_with_months):
    current = next(s for s in wheat_fallow_with_months["strategies"] if s["is_current"])
    assert "gap_default_months" not in _gap_codes(current), _gap_codes(current)
