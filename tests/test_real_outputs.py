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


def _assert_no_sentinels(obj):
    bad = [(p, v) for p, v in _walk_numbers(obj) if v <= -999]
    assert not bad, f"sentinel values (<= -999) found: {bad[:5]}"


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
