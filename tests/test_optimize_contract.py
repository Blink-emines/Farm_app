"""Contract tests for POST /api/optimize (docs/contracts/optimize.schema.json).

The optimize schema references strategy.schema.json by its absolute $id, so
the schemas are registered together before validating.
"""

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from tests.conftest import CONTRACTS, PRIORITY_KEYS, _load

OPTIMIZE_SCHEMA_PATH = CONTRACTS / "optimize.schema.json"


@pytest.fixture(scope="module")
def optimize_validator():
    optimize = _load(OPTIMIZE_SCHEMA_PATH)
    strategy = _load(CONTRACTS / "strategy.schema.json")
    registry = Registry().with_resources([
        (strategy["$id"], Resource.from_contents(strategy, default_specification=DRAFT202012)),
    ])
    return Draft202012Validator(optimize, registry=registry, format_checker=FormatChecker())


def _parcel(pid, area, irrigated, seasons):
    return {
        "id": pid,
        "area_ha": area,
        "irrigated": irrigated,
        "current_rotation": {"seasons": seasons},
    }


def valid_request():
    return {
        "latitude": 33.96,
        "longitude": -5.27,
        "profile": "balanced",
        "pareto_points": 4,
        "parcels": [
            _parcel("rain1", 3.0, False, [{"crop_id": "wheat"}, {"crop_id": "fallow"}]),
            _parcel("irr1", 2.0, True, [{"crop_id": "barley"}]),
        ],
    }


def test_optimize_schema_is_valid_draft_2020_12():
    Draft202012Validator.check_schema(_load(OPTIMIZE_SCHEMA_PATH))


def test_valid_request_passes_request_schema():
    request_def = {**_load(OPTIMIZE_SCHEMA_PATH), "$ref": "#/$defs/OptimizeRequest"}
    strategy = _load(CONTRACTS / "strategy.schema.json")
    registry = Registry().with_resources([
        (strategy["$id"], Resource.from_contents(strategy, default_specification=DRAFT202012)),
    ])
    validator = Draft202012Validator(request_def, registry=registry, format_checker=FormatChecker())
    errors = list(validator.iter_errors(valid_request()))
    assert errors == [], [e.message for e in errors]


def test_request_with_profile_and_priorities_is_rejected(optimize_validator):
    request = valid_request()
    request["priorities"] = {k: 3 for k in PRIORITY_KEYS}
    request_def = {**_load(OPTIMIZE_SCHEMA_PATH), "$ref": "#/$defs/OptimizeRequest"}
    strategy = _load(CONTRACTS / "strategy.schema.json")
    registry = Registry().with_resources([
        (strategy["$id"], Resource.from_contents(strategy, default_specification=DRAFT202012)),
    ])
    validator = Draft202012Validator(request_def, registry=registry, format_checker=FormatChecker())
    assert list(validator.iter_errors(request))


def test_request_with_zero_area_parcel_is_rejected():
    request = valid_request()
    request["parcels"][0]["area_ha"] = 0
    request_def = {**_load(OPTIMIZE_SCHEMA_PATH), "$ref": "#/$defs/OptimizeRequest"}
    strategy = _load(CONTRACTS / "strategy.schema.json")
    registry = Registry().with_resources([
        (strategy["$id"], Resource.from_contents(strategy, default_specification=DRAFT202012)),
    ])
    validator = Draft202012Validator(request_def, registry=registry, format_checker=FormatChecker())
    assert list(validator.iter_errors(request))


def test_request_with_unknown_crop_is_rejected():
    request = valid_request()
    request["parcels"][0]["current_rotation"]["seasons"] = [{"crop_id": "tomato"}]
    request_def = {**_load(OPTIMIZE_SCHEMA_PATH), "$ref": "#/$defs/OptimizeRequest"}
    strategy = _load(CONTRACTS / "strategy.schema.json")
    registry = Registry().with_resources([
        (strategy["$id"], Resource.from_contents(strategy, default_specification=DRAFT202012)),
    ])
    validator = Draft202012Validator(request_def, registry=registry, format_checker=FormatChecker())
    assert list(validator.iter_errors(request))
