"""Shared fixtures for the cross-part contract tests.

Loads the two JSON Schemas in docs/contracts/ and builds small, hand-made
examples that are valid by hand. The negative tests copy these examples and
break one thing at a time.
"""

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACTS = REPO_ROOT / "docs" / "contracts"
FEATURES_SCHEMA_PATH = CONTRACTS / "features.schema.json"
STRATEGY_SCHEMA_PATH = CONTRACTS / "strategy.schema.json"

PRIORITY_KEYS = ["save_water", "improve_soil", "extra_income", "reduce_erosion", "forage"]


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="session")
def features_schema():
    return _load(FEATURES_SCHEMA_PATH)


@pytest.fixture(scope="session")
def strategy_schema():
    return _load(STRATEGY_SCHEMA_PATH)


def make_validator(schema):
    """Validator with format checking on (date-time, uri)."""
    return Draft202012Validator(schema, format_checker=FormatChecker())


@pytest.fixture(scope="session")
def features_validator(features_schema):
    return make_validator(features_schema)


@pytest.fixture(scope="session")
def strategy_validator(strategy_schema):
    return make_validator(strategy_schema)


# ---------------------------------------------------------------------------
# Hand-made valid features.json
# ---------------------------------------------------------------------------

def _series(unit, value, source="nasa_power", method="test value", parameter="T2M"):
    return {
        "values": [value] * 12,
        "unit": unit,
        "source": source,
        "method": method,
        "nasa_parameter": parameter,
    }


def _heat_days():
    return {
        "30": _series("days/month", 5.0),
        "32": _series("days/month", 3.0),
        "35": _series("days/month", 1.0),
        "38": _series("days/month", 0.0),
    }


def make_features():
    """A valid features.json with no soil data (status unavailable)."""
    return {
        "schema_version": "1.0",
        "generated_at": "2026-11-01T10:00:00Z",
        "location": {
            "latitude": 33.96,
            "longitude": -5.27,
            "elevation_m": 500.0,
            "region": "saiss",
        },
        "climate": {
            "period": {"start_year": 2005, "end_year": 2024},
            "monthly": {
                "t2m_mean": _series("°C", 18.0, parameter="T2M"),
                "t2m_max": _series("°C", 24.0, parameter="T2M_MAX"),
                "t2m_min": _series("°C", 12.0, parameter="T2M_MIN"),
                "precipitation": _series("mm/month", 40.0, parameter="PRECTOTCORR"),
                "et0": _series("mm/month", 90.0, source="computed", parameter=None),
                "water_balance": _series("mm/month", -50.0, source="computed", parameter=None),
                "rh2m": _series("%", 60.0, parameter="RH2M"),
                "ws2m": _series("m/s", 3.0, parameter="WS2M"),
                "solar_radiation": _series("MJ/m²/day", 20.0, parameter="ALLSKY_SFC_SW_DWN"),
                "root_zone_wetness": _series("0-1", 0.3, source="nasa_power", parameter="GWETROOT"),
                "frost_days": _series("days/month", 0.5, parameter="T2M_MIN"),
                "heat_days": _heat_days(),
            },
        },
        "soil": {"status": "unavailable", "source": None, "layers": []},
        "data_gaps": [
            {
                "code": "soil_unavailable",
                "message": "No soil data could be retrieved for this point.",
                "affects": ["soil"],
            }
        ],
        "sources": [
            {
                "id": "nasa_power",
                "name": "NASA POWER",
                "dataset": "NASA POWER daily point API, community AG",
                "url": "https://power.larc.nasa.gov/api/temporal/daily/point",
                "accessed_at": "2026-11-01T09:59:00Z",
                "cache_status": "live",
            }
        ],
    }


# ---------------------------------------------------------------------------
# Hand-made valid StrategyResponse
# ---------------------------------------------------------------------------

def _msg(code, text="Example text"):
    return {"code": code, "params": {}, "default_text": text}


def _season(crop, sow, harvest):
    return {"crop_id": crop, "sow_month": sow, "harvest_month": harvest}


def _calendar(seasons):
    """One 12-month row per season, as the schema requires."""
    rows = []
    for year, season in enumerate(seasons, start=1):
        months = []
        for m in range(1, 13):
            crop = season["crop_id"]
            sow, harvest = season["sow_month"], season["harvest_month"]
            if sow <= harvest:
                in_window = sow <= m <= harvest
            else:  # season wraps over the new year, e.g. sow Nov, harvest Jun
                in_window = m >= sow or m <= harvest
            in_field = crop != "fallow" and in_window
            months.append(
                {
                    "month": m,
                    "crop_id": crop if in_field else None,
                    "status": "growing" if in_field else "bare",
                    "stress_reasons": [],
                }
            )
        rows.append({"year": year, "months": months})
    return rows


def _by_priority(total):
    return {k: float(total) for k in PRIORITY_KEYS}


def make_strategy(strategy_id, rank, total, is_current=False, seasons=None):
    seasons = seasons or [_season("wheat", 11, 6)]
    return {
        "id": strategy_id,
        "name": _msg(f"strategy_{strategy_id}", strategy_id),
        "is_current": is_current,
        "rank": rank,
        "score": {"total": total, "by_priority": _by_priority(total)},
        "seasons": seasons,
        "calendar": _calendar(seasons),
        "why": [
            {
                "rule_id": "water_balance_rule",
                "effect": "bonus",
                "points": total,
                "priority": "save_water",
                "message": _msg("why_water_balance"),
            }
        ],
        "evidence": [
            {
                "feature": "climate.monthly.water_balance",
                "value": [-50.0] * 12,
                "unit": "mm/month",
                "months": [1, 2, 3],
                "source": "NASA POWER",
            }
        ],
        "benefits": [_msg("benefit_example")],
        "information_gaps": [],
        "risks_for_local_review": [_msg("risk_example")],
        "confidence": "medium",
    }


def make_strategy_response():
    """A valid StrategyResponse: three strategies, one of them current."""
    return {
        "schema_version": "1.0",
        "generated_at": "2026-11-01T10:00:01Z",
        "location": {"latitude": 33.96, "longitude": -5.27},
        "features_summary": {
            "climate_period": {"start_year": 2005, "end_year": 2024},
            "soil_status": "unavailable",
            "data_gaps": ["soil_unavailable"],
        },
        "priorities": {k: 3 for k in PRIORITY_KEYS},
        "strategies": [
            make_strategy("wheat_chickpea", 1, 80.0, is_current=True),
            make_strategy("wheat_fallow", 2, 70.0),
            make_strategy("wheat_lentil", 3, 60.0),
        ],
        "notes": [
            _msg("note_relative_scores"),
            _msg("note_local_expert"),
        ],
    }


def copy_of(obj):
    return copy.deepcopy(obj)
