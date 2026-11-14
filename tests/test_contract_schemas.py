"""Contract tests: the two JSON Schemas and hand-made examples.

These tests need no other part of the app. They prove that:
- both schema files are valid Draft 2020-12 documents;
- hand-made valid examples pass;
- broken examples are rejected for the reason the contract gives.

Rules that JSON Schema cannot express (sorted ranks, calendar length,
etc.) are tested in test_real_outputs.py instead.
"""

import copy

import pytest
from jsonschema import Draft202012Validator

from tests.conftest import (
    PRIORITY_KEYS,
    make_features,
    make_strategy_response,
    make_validator,
)


# ---------------------------------------------------------------------------
# Both schemas are valid Draft 2020-12
# ---------------------------------------------------------------------------

def test_features_schema_is_valid_draft_2020_12(features_schema):
    Draft202012Validator.check_schema(features_schema)


def test_strategy_schema_is_valid_draft_2020_12(strategy_schema):
    Draft202012Validator.check_schema(strategy_schema)


# ---------------------------------------------------------------------------
# Hand-made valid examples pass
# ---------------------------------------------------------------------------

def test_valid_features_example_passes(features_validator):
    errors = list(features_validator.iter_errors(make_features()))
    assert errors == [], [e.message for e in errors]


def test_valid_strategy_response_example_passes(strategy_validator):
    errors = list(strategy_validator.iter_errors(make_strategy_response()))
    assert errors == [], [e.message for e in errors]


def test_valid_strategy_request_example_passes(strategy_schema):
    request = {
        "latitude": 33.96,
        "longitude": -5.27,
        "current_rotation": {
            "seasons": [
                {"crop_id": "wheat"},
                {"crop_id": "fallow", "sow_month": 10, "harvest_month": 6},
            ]
        },
        "priorities": {k: 3 for k in PRIORITY_KEYS},
    }
    validator = make_validator({**strategy_schema, "$ref": "#/$defs/StrategyRequest"})
    errors = list(validator.iter_errors(request))
    assert errors == [], [e.message for e in errors]


# ---------------------------------------------------------------------------
# Invalid features examples are rejected
# ---------------------------------------------------------------------------

def _features_mutation(mutate):
    obj = make_features()
    mutate(obj)
    return obj


def _set_monthly(obj, name, **changes):
    obj["climate"]["monthly"][name].update(changes)


FEATURES_INVALID = {
    "wrong unit for t2m_mean (Fahrenheit instead of °C)": lambda o: _set_monthly(o, "t2m_mean", unit="°F"),
    "11 monthly values instead of 12": lambda o: _set_monthly(o, "precipitation", values=[40.0] * 11),
    "13 monthly values instead of 12": lambda o: _set_monthly(o, "precipitation", values=[40.0] * 13),
    "soil status outside the enum": lambda o: o["soil"].update(status="guessed"),
    "clay_pct of -999 (sentinel used as a percentage)": lambda o: o["soil"].update(
        status="live",
        source="isric_soilgrids",
        layers=[{
            "depth": "0-5cm",
            "clay_pct": -999,
            "sand_pct": 30.0,
            "silt_pct": 20.0,
            "soc_g_kg": 8.0,
            "ph_h2o": 7.8,
        }],
    ),
    "clay_pct above 100": lambda o: o["soil"].update(
        status="live",
        source="isric_soilgrids",
        layers=[{
            "depth": "0-5cm",
            "clay_pct": 120.0,
            "sand_pct": 30.0,
            "silt_pct": 20.0,
            "soc_g_kg": 8.0,
            "ph_h2o": 7.8,
        }],
    ),
    "heat_days threshold key 33 (not one of 30/32/35/38)": lambda o: o["climate"]["monthly"]["heat_days"].update(
        {"33": _series_like("days/month")}
    ),
    "region is not saiss": lambda o: o["location"].update(region="chaouia"),
    "unknown top-level field": lambda o: o.update(extra="nope"),
}


def _series_like(unit):
    return {
        "values": [1.0] * 12,
        "unit": unit,
        "source": "nasa_power",
        "method": "test",
        "nasa_parameter": None,
    }


@pytest.mark.parametrize("label", list(FEATURES_INVALID))
def test_invalid_features_example_is_rejected(features_validator, label):
    obj = _features_mutation(FEATURES_INVALID[label])
    assert list(features_validator.iter_errors(obj)), f"expected rejection: {label}"


# ---------------------------------------------------------------------------
# Invalid StrategyResponse examples are rejected
# ---------------------------------------------------------------------------

def _response_mutation(mutate):
    obj = make_strategy_response()
    mutate(obj)
    return obj


def _set_strategy(obj, index, **changes):
    obj["strategies"][index].update(changes)


def _two_current(obj):
    obj["strategies"][1]["is_current"] = True


def _no_current(obj):
    obj["strategies"][0]["is_current"] = False


def _priority_six(obj):
    obj["priorities"]["save_water"] = 6


def _empty_why(obj):
    _set_strategy(obj, 0, why=[])


def _empty_risks(obj):
    _set_strategy(obj, 0, risks_for_local_review=[])


def _bad_crop(obj):
    obj["strategies"][0]["seasons"][0]["crop_id"] = "tomato"
    obj["strategies"][0]["calendar"][0]["months"][0]["crop_id"] = "tomato"


def _only_two_strategies(obj):
    obj["strategies"] = obj["strategies"][:2]


def _calendar_eleven_months(obj):
    obj["strategies"][0]["calendar"][0]["months"] = obj["strategies"][0]["calendar"][0]["months"][:11]


def _score_out_of_range(obj):
    _set_strategy(obj, 0, score={"total": 120.0, "by_priority": obj["strategies"][0]["score"]["by_priority"]})


def _missing_one_notes(obj):
    obj["notes"] = obj["notes"][:1]


STRATEGY_INVALID = {
    "two current strategies": _two_current,
    "no current strategy": _no_current,
    "priority 6 in priorities (max is 5)": _priority_six,
    "score with an empty why list": _empty_why,
    "empty risks_for_local_review": _empty_risks,
    "crop not in the crop list": _bad_crop,
    "only 2 strategies (minimum is 3)": _only_two_strategies,
    "calendar row with 11 months": _calendar_eleven_months,
    "total score above 100": _score_out_of_range,
    "only 1 note (minimum is 2)": _missing_one_notes,
}


@pytest.mark.parametrize("label", list(STRATEGY_INVALID))
def test_invalid_strategy_response_is_rejected(strategy_validator, label):
    obj = _response_mutation(STRATEGY_INVALID[label])
    assert list(strategy_validator.iter_errors(obj)), f"expected rejection: {label}"


def test_strategy_response_soil_status_outside_enum_is_rejected(strategy_validator):
    obj = make_strategy_response()
    obj["features_summary"]["soil_status"] = "guessed"
    assert list(strategy_validator.iter_errors(obj))


def test_strategy_priority_above_five_is_rejected_in_request(strategy_schema):
    request = {
        "latitude": 33.96,
        "longitude": -5.27,
        "current_rotation": {"seasons": [{"crop_id": "wheat"}]},
        "priorities": {k: 3 for k in PRIORITY_KEYS} | {"forage": 6},
    }
    validator = make_validator({**strategy_schema, "$ref": "#/$defs/StrategyRequest"})
    assert list(validator.iter_errors(request))


def test_strategy_request_with_unknown_crop_is_rejected(strategy_schema):
    request = {
        "latitude": 33.96,
        "longitude": -5.27,
        "current_rotation": {"seasons": [{"crop_id": "tomato"}]},
        "priorities": {k: 3 for k in PRIORITY_KEYS},
    }
    validator = make_validator({**strategy_schema, "$ref": "#/$defs/StrategyRequest"})
    assert list(validator.iter_errors(request))


def test_score_of_minus_999_is_rejected(strategy_validator):
    # A score is 0-100. The -999 sentinel must never reach a score.
    obj = make_strategy_response()
    obj["strategies"][0]["score"]["total"] = -999
    assert list(strategy_validator.iter_errors(obj))
