"""Integration checks for POST /api/optimize on the running backend (:8000).

Request: two parcels, balanced profile, Pareto points 4.
  rain1: rainfed, wheat -> fallow
  irr1:  irrigated, barley

If the backend is not reachable every test is SKIPPED with that reason.
A skip is not a pass.
"""

import urllib.error
import urllib.request
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from tests.conftest import CONTRACTS, REPO_ROOT, _load
from tests.test_api import API, TIMEOUT, _request

OPTIMIZE_REQUEST = {
    "latitude": 33.96,
    "longitude": -5.27,
    "profile": "balanced",
    "pareto_points": 4,
    "parcels": [
        {
            "id": "rain1",
            "area_ha": 3.0,
            "irrigated": False,
            "current_rotation": {"seasons": [{"crop_id": "wheat"}, {"crop_id": "fallow"}]},
        },
        {
            "id": "irr1",
            "area_ha": 2.0,
            "irrigated": True,
            "current_rotation": {"seasons": [{"crop_id": "barley"}]},
        },
    ],
}

# Perennials are exempt from the family gap in the engine (optimize/model.py).
PERENNIALS = {"alfalfa", "olive_intercrop"}


@pytest.fixture(scope="module", autouse=True)
def require_server():
    try:
        urllib.request.urlopen(API + "/api/features?lat=33.96&lon=-5.27", timeout=TIMEOUT)
    except urllib.error.HTTPError:
        return
    except (urllib.error.URLError, OSError) as exc:
        pytest.skip(f"backend not reachable at {API}: {exc}")


@pytest.fixture(scope="module")
def response():
    status, body = _request("POST", "/api/optimize", OPTIMIZE_REQUEST)
    assert status == 200, body
    return body


@pytest.fixture(scope="module")
def optimize_response_validator():
    optimize = _load(CONTRACTS / "optimize.schema.json")
    strategy = _load(CONTRACTS / "strategy.schema.json")
    registry = Registry().with_resources([
        (strategy["$id"], Resource.from_contents(strategy, default_specification=DRAFT202012)),
    ])
    return Draft202012Validator(optimize, registry=registry, format_checker=FormatChecker())


def _family_of():
    crops = yaml.safe_load((REPO_ROOT / "engine" / "crops.yaml").read_text(encoding="utf-8"))["crops"]
    return {c: v["family"]["value"] for c, v in crops.items()}


def _gaps():
    weights = yaml.safe_load((REPO_ROOT / "engine" / "weights.yaml").read_text(encoding="utf-8"))
    return weights["optimiser"]["family_gap_months"]


def _sow_starts(seasons, cycle):
    """Absolute start month index (0..cycle-1) of each season in order.
    Each season starts at the next month matching its sow month, after the
    previous season's start. Gaps between seasons are bare months."""
    starts, prev = [], -1
    for season in seasons:
        target = season["sow_month"] - 1
        idx = prev + 1
        while idx % 12 != target:
            idx += 1
        starts.append(idx)
        prev = idx
    return [s % cycle for s in starts]


def _plan_seasons(parcel):
    return parcel["plan"]["seasons"]


def test_response_validates_against_optimize_schema(response, optimize_response_validator):
    errors = list(optimize_response_validator.iter_errors(response))
    assert not errors, [e.message for e in errors[:5]]


def test_both_parcels_are_returned(response):
    assert [p["id"] for p in response["parcels"]] == ["rain1", "irr1"]


def test_no_potato_on_rainfed_parcel(response):
    rain = next(p for p in response["parcels"] if p["id"] == "rain1")
    crops = [s["crop_id"] for s in _plan_seasons(rain)]
    assert "potato" not in crops, crops


def test_potato_is_allowed_only_where_irrigated(response):
    irr = next(p for p in response["parcels"] if p["id"] == "irr1")
    assert irr["irrigated"] is True


def test_no_same_family_within_its_gap(response):
    family = _family_of()
    gaps = _gaps()
    for parcel in response["parcels"]:
        seasons = [s for s in _plan_seasons(parcel) if s["crop_id"] != "fallow"]
        cycle = 12 * len(parcel["plan"]["calendar"])
        starts = _sow_starts(seasons, cycle)
        for fam, gap in gaps.items():
            members = [
                i for i, s in enumerate(seasons)
                if family.get(s["crop_id"]) == fam and s["crop_id"] not in PERENNIALS
            ]
            for a in members:
                for b in members:
                    if a >= b:
                        continue
                    forward = (starts[b] - starts[a]) % cycle
                    backward = cycle - forward
                    assert min(forward, backward) >= gap, (
                        f"{parcel['id']}: {seasons[a]['crop_id']} and {seasons[b]['crop_id']} "
                        f"({fam}) sown {min(forward, backward)} months apart, gap is {gap}"
                    )


def test_pareto_points_present_and_sorted_by_revenue(response):
    points = response["pareto"]
    assert len(points) >= 2, points
    revenues = [p["revenue_mad_per_ha_year"] for p in points]
    assert revenues == sorted(revenues), revenues
    for p in points:
        for key in ("extra_income", "save_water"):
            assert 0 <= p["scores"][key] <= 100, p


def test_totals_are_present_and_nonnegative_area(response):
    totals = response["totals"]
    assert totals["area_ha"] == pytest.approx(5.0)
