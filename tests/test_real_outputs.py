"""Contract tests on REAL outputs of data/ and engine/.

Each test skips with a clear reason while its part does not exist yet.
A skip is never a pass: in the final report, a skipped test counts as
not verified.
"""

import json
import numbers

import pytest

from tests.conftest import PRIORITY_KEYS, REPO_ROOT

FEATURES_SAMPLE = REPO_ROOT / "data" / "samples" / "features_default.json"
SCORER_PATH = REPO_ROOT / "engine" / "scorer.py"

DEFAULT_REQUEST = {
    "latitude": 33.96,
    "longitude": -5.27,
    "current_rotation": {
        "seasons": [
            {"crop_id": "wheat"},
            {"crop_id": "fallow"},
        ]
    },
    "priorities": {"save_water": 4, "improve_soil": 3, "extra_income": 3,
                   "reduce_erosion": 2, "forage": 1},
}


def _require_features_sample():
    if not FEATURES_SAMPLE.exists():
        pytest.skip(f"data/samples/features_default.json not built yet ({FEATURES_SAMPLE})")
    with open(FEATURES_SAMPLE, encoding="utf-8") as fh:
        return json.load(fh)


def _require_scorer():
    if not SCORER_PATH.exists():
        pytest.skip(f"engine/scorer.py not built yet ({SCORER_PATH})")
    try:
        from engine.scorer import score  # noqa: WPS433 (import inside test on purpose)
    except ImportError as exc:
        pytest.skip(f"engine.scorer.score cannot be imported yet: {exc}")
    return score


def _walk_numbers(obj, path="$"):
    """Yield (path, value) for every number in a JSON-like structure."""
    if isinstance(obj, bool):
        return
    if isinstance(obj, numbers.Number):
        yield path, obj
    elif isinstance(obj, dict):
        for key, value in obj.items():
            yield from _walk_numbers(value, f"{path}.{key}")
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            yield from _walk_numbers(value, f"{path}[{index}]")


# Exact missing-data sentinels. A value like -1338 mm of water balance is
# real (dry years), so we do not use a "<= -999" threshold.
SENTINELS = {-999, -999.0, -9999, -9999.0, -99, -99.0}


def _assert_no_sentinels(obj):
    bad = [(p, v) for p, v in _walk_numbers(obj) if v in SENTINELS or v != v]
    assert not bad, f"sentinel or NaN values found: {bad[:5]}"


def _assert_valid(validator, obj):
    errors = sorted(validator.iter_errors(obj), key=lambda e: list(e.absolute_path))
    assert not errors, "; ".join(f"{list(e.absolute_path)}: {e.message}" for e in errors[:5])


# ---------------------------------------------------------------------------
# data/ : features sample
# ---------------------------------------------------------------------------

def test_features_sample_is_valid_against_schema(features_validator):
    features = _require_features_sample()
    _assert_valid(features_validator, features)


def test_features_sample_has_no_sentinel_values():
    features = _require_features_sample()
    _assert_no_sentinels(features)


def _in_range(v, lo, hi):
    return v is None or lo <= v <= hi


# Plausible physical ranges per unit. water_balance is excluded from the
# "non-negative" rule on purpose: it is legitimately negative.
UNIT_RANGES = {
    "°C": (-30, 60),
    "%": (0, 100),
    "0-1": (0, 1),
    "m/s": (0, 30),
    "MJ/m²/day": (0, 40),
    "days/month": (0, 31),
    "mm/month": (0, 2000),
}


def test_features_sample_monthly_values_in_plausible_ranges():
    features = _require_features_sample()
    for name, series in features["climate"]["monthly"].items():
        if name == "heat_days":
            subseries = series.values()
        else:
            subseries = [series]
        for s in subseries:
            if name == "water_balance":
                lo, hi = -3000, 2000
            else:
                lo, hi = UNIT_RANGES[s["unit"]]
            bad = [v for v in s["values"] if not _in_range(v, lo, hi)]
            assert not bad, f"{name} ({s['unit']}) out of range {lo}..{hi}: {bad[:3]}"


def test_features_sample_yearly_values_in_plausible_ranges():
    features = _require_features_sample()
    yearly = features["yearly"]
    for key in ("precipitation", "et0", "frost_days", "heat_days_35"):
        bad = [v for v in yearly[key] if not _in_range(v, 0, 5000)]
        assert not bad, f"yearly {key} out of range: {bad[:3]}"
    # water_balance is precipitation minus et0 per year: may be negative.
    for year_index, wb in enumerate(yearly["water_balance"]):
        if wb is None:
            continue
        expected = yearly["precipitation"][year_index] - yearly["et0"][year_index]
        assert abs(wb - expected) < 1.0, (year_index, wb, expected)


def test_features_sample_soil_layers_in_plausible_ranges():
    features = _require_features_sample()
    for layer in features["soil"]["layers"]:
        for key in ("clay_pct", "sand_pct", "silt_pct"):
            assert _in_range(layer[key], 0, 100), (layer["depth"], key, layer[key])
        assert _in_range(layer["ph_h2o"], 0, 14), (layer["depth"], layer["ph_h2o"])
        assert layer["soc_g_kg"] is None or layer["soc_g_kg"] >= 0, layer


def test_features_sample_data_gaps_are_well_formed():
    features = _require_features_sample()
    for gap in features["data_gaps"]:
        assert gap["code"] and gap["message"], gap


def test_features_sample_sources_cover_every_referenced_source_id():
    features = _require_features_sample()
    known = {s["id"] for s in features["sources"]}
    referenced = set()
    if features["soil"]["source"]:
        referenced.add(features["soil"]["source"])
    for name, series in features["climate"]["monthly"].items():
        if name == "heat_days":
            referenced.update(v["source"] for v in series.values())
        else:
            referenced.add(series["source"])
    missing = referenced - known
    assert not missing, f"source ids used but not listed in sources: {sorted(missing)}"


# ---------------------------------------------------------------------------
# engine/ : score() output on the sample
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def scored():
    score = _require_scorer()
    features = _require_features_sample()
    return score(features, DEFAULT_REQUEST)


def test_score_output_is_valid_against_strategy_schema(strategy_validator, scored):
    _assert_valid(strategy_validator, scored)


def test_score_output_has_no_sentinel_values(scored):
    _assert_no_sentinels(scored)


def test_score_output_has_exactly_one_current_strategy(scored):
    current = [s for s in scored["strategies"] if s["is_current"]]
    assert len(current) == 1, f"found {len(current)} current strategies"


def test_score_output_ranks_are_one_to_n_and_sorted(scored):
    strategies = scored["strategies"]
    ranks = [s["rank"] for s in strategies]
    assert ranks == list(range(1, len(strategies) + 1)), ranks


def test_score_output_calendar_length_matches_seasons(scored):
    for s in scored["strategies"]:
        assert len(s["calendar"]) == len(s["seasons"]), s["id"]


def test_score_output_every_strategy_has_a_why_and_risks(scored):
    for s in scored["strategies"]:
        assert s["why"], f"{s['id']} has no why entries"
        assert s["risks_for_local_review"], f"{s['id']} has no risks"
        assert s["evidence"], f"{s['id']} has no evidence"


def test_score_output_why_points_are_finite_and_priorities_known(scored):
    for s in scored["strategies"]:
        for entry in s["why"]:
            assert entry["priority"] in PRIORITY_KEYS, entry
            assert entry["points"] == entry["points"], entry  # not NaN


def test_score_output_features_summary_data_gaps_match_features_codes(scored):
    features = _require_features_sample()
    expected = [g["code"] for g in features["data_gaps"]]
    assert scored["features_summary"]["data_gaps"] == expected


def test_score_output_soil_status_matches_features(scored):
    features = _require_features_sample()
    assert scored["features_summary"]["soil_status"] == features["soil"]["status"]


def test_score_output_climate_period_matches_features(scored):
    features = _require_features_sample()
    assert scored["features_summary"]["climate_period"] == features["climate"]["period"]


def test_score_output_notes_mention_relative_scores_and_local_expert(scored):
    texts = " ".join(n["default_text"].lower() for n in scored["notes"])
    assert "relative" in texts, texts
    assert "expert" in texts, texts


def test_score_output_location_matches_request(scored):
    assert scored["location"] == {
        "latitude": DEFAULT_REQUEST["latitude"],
        "longitude": DEFAULT_REQUEST["longitude"],
    }
