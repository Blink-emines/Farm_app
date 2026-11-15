import copy
import json

import pytest

from engine import messages
from engine.loaders import UNKNOWN, load_crops, validators
from engine.scorer import MonthsUnknown, minmax, resolve_seasons, score
from engine.tests.conftest import REAL_SAMPLE


def test_output_validates_and_shape(features_mock, request_default):
    out = score(features_mock, request_default)
    assert validators()[2].is_valid(out)
    assert 3 <= len(out["strategies"]) <= 5
    assert sum(s["is_current"] for s in out["strategies"]) == 1
    assert [s["rank"] for s in out["strategies"]] == list(range(1, len(out["strategies"]) + 1))
    totals = [s["score"]["total"] for s in out["strategies"]]
    assert totals == sorted(totals, reverse=True)


def test_every_score_traces_to_a_rule(features_mock, request_default):
    out = score(features_mock, request_default)
    for s in out["strategies"]:
        assert s["why"] and all(w["rule_id"] and w["message"]["code"] for w in s["why"])


def test_features_summary_gap_codes_exact(features_mock, request_default):
    out = score(features_mock, request_default)
    assert out["features_summary"]["data_gaps"] == [g["code"] for g in features_mock["data_gaps"]]


def test_local_prices_always_a_gap(features_mock, request_default):
    for s in score(features_mock, request_default)["strategies"]:
        assert any(g["code"] == "gap_local_prices" for g in s["information_gaps"])


def test_frost_underestimated_gap_when_growing_in_winter(features_mock, request_default):
    for s in score(features_mock, request_default)["strategies"]:
        winter = any(c["crop_id"] not in (None, "fallow") and c["month"] in (12, 1, 2)
                     for r in s["calendar"] for c in r["months"])
        has = any(g["code"] == "gap_frost_underestimated" for g in s["information_gaps"])
        assert winter == has


def test_frost_heat_gives_no_score_points(features_mock, request_default):
    for s in score(features_mock, request_default)["strategies"]:
        assert not any("frost" in w["rule_id"] or "heat" in w["rule_id"] for w in s["why"])
        assert any(r["code"] == "risk_frost_heat_unassessed" for r in s["risks_for_local_review"])


def test_request_months_override_defaults(features_mock, request_default):
    request_default["current_rotation"]["seasons"][0].update(sow_month=2, harvest_month=9)
    cur = next(s for s in score(features_mock, request_default)["strategies"] if s["is_current"])
    assert cur["seasons"][0]["sow_month"] == 2 and cur["seasons"][0]["harvest_month"] == 9


def test_defaults_lower_confidence(features_mock, request_default):
    out = score(features_mock, request_default)
    for s in out["strategies"]:
        if any(g["code"] == "gap_default_months" for g in s["information_gaps"]):
            assert s["confidence"] == "low"


def test_unknown_months_raise(features_mock, request_default, crops):
    crops = copy.deepcopy(crops)
    crops["wheat"]["sow_month"]["value"] = UNKNOWN
    with pytest.raises(MonthsUnknown):
        score(features_mock, request_default, crops=crops)


def test_current_equal_to_template_is_shown_once(features_mock, request_default):
    request_default["current_rotation"]["seasons"] = [{"crop_id": "wheat"}, {"crop_id": "chickpea"}]
    out = score(features_mock, request_default)
    assert sum(1 for s in out["strategies"] if s["name"]["params"]["crops"] == "wheat > chickpea") == 1


def test_all_zero_priorities_means_equal_weights(features_mock, request_default):
    request_default["priorities"] = {k: 0 for k in request_default["priorities"]}
    assert validators()[2].is_valid(score(features_mock, request_default))


def test_priority_weights_change_ranking_inputs(features_mock, request_default):
    a = score(features_mock, request_default)
    request_default["priorities"] = {"save_water": 0, "improve_soil": 0, "extra_income": 0,
                                     "reduce_erosion": 0, "forage": 5}
    b = score(features_mock, request_default)
    assert a["strategies"][0]["score"]["total"] != b["strategies"][0]["score"]["total"] or \
        a["strategies"][0]["id"] != b["strategies"][0]["id"]


def test_normalise_over_returned_option(features_mock, request_default, weights):
    w = copy.deepcopy(weights)
    w["normalise_over"] = "returned"
    out = score(features_mock, request_default, weights=w)
    bp = [s["score"]["by_priority"]["improve_soil"] for s in out["strategies"]]
    assert min(bp) == 0 and max(bp) == 100  # stretched over the returned set only


def test_minmax():
    assert minmax([1, 2, 3]) == [0, 50, 100]
    assert minmax([4, 4]) == [50, 50]


def test_invalid_request_rejected(features_mock, request_default):
    request_default["priorities"]["save_water"] = 9
    with pytest.raises(ValueError):
        score(features_mock, request_default)


def test_real_sample_validates(request_default):
    features = json.loads(REAL_SAMPLE.read_text())
    out = score(features, request_default)
    assert validators()[2].is_valid(out)
    assert out["features_summary"]["data_gaps"] == [g["code"] for g in features["data_gaps"]]


def test_messages_md_in_sync():
    from pathlib import Path
    md = (Path(messages.__file__).parent / "messages.md").read_text()
    assert md == messages.render_markdown()


def test_every_emitted_code_is_registered(features_mock, request_default):
    out = score(features_mock, request_default)
    def codes(o):
        if isinstance(o, dict):
            if "code" in o and "default_text" in o:
                yield o["code"]
            for v in o.values():
                yield from codes(v)
        elif isinstance(o, list):
            for v in o:
                yield from codes(v)
    assert set(codes(out)) <= set(messages.MESSAGES)


def test_crops_yaml_every_value_has_source_and_no_invented_kc():
    crops = load_crops()
    assert len(crops) == 11
    for cid, fields in crops.items():
        for name, e in fields.items():
            assert "value" in e and e["source"], (cid, name)
    assert crops["vetch_oat_cover"]["kc_mid"]["source"].startswith("proxy")
    assert crops["fallow"]["kc_mid"]["value"] == UNKNOWN
    for cid, f in crops.items():
        for k in ("sow_month", "harvest_month"):
            if cid != "fallow":
                assert f[k]["source"] == "default approved by user 2026-11-14, to confirm locally"
    assert crops["faba_bean"]["sow_month"]["value"] == 11 and "user decision" in crops["faba_bean"]["sow_month"]["basis"]
    assert crops["faba_bean"]["income_flag"]["value"] == crops["alfalfa"]["income_flag"]["value"] == "medium"


def test_water_indicative_gap_always_present(features_mock, request_default):
    for s in score(features_mock, request_default)["strategies"]:
        assert any(g["code"] == "gap_water_stress_indicative" for g in s["information_gaps"])


def test_current_wheat_fallow_on_real_sample():
    features = json.loads(REAL_SAMPLE.read_text())
    req = {"latitude": 33.96, "longitude": -5.27,
           "current_rotation": {"seasons": [{"crop_id": "wheat"}, {"crop_id": "fallow"}]},
           "priorities": {"save_water": 3, "improve_soil": 3, "extra_income": 2, "reduce_erosion": 1, "forage": 0}}
    cur = next(s for s in score(features, req)["strategies"] if s["is_current"])
    cells = [c for r in cur["calendar"] for c in r["months"]]
    assert sum(c["status"] == "bare" for c in cells) == 16
    bare = next(w for w in cur["why"] if w["rule_id"] == "bare_months_penalty")
    assert bare["message"]["params"]["count"] == 16


def test_soil_steps_add_up_to_the_improve_soil_points(features_mock, request_default):
    for s in score(features_mock, request_default)["strategies"]:
        soil_why = sum(w["points"] for w in s["why"] if w["priority"] == "improve_soil")
        assert len(s["soil_steps"]) == len(s["seasons"])
        assert abs(sum(st["points"] for st in s["soil_steps"]) - soil_why) < 0.05, s["id"]


def test_soil_step_credits_the_legume_after_the_cereal(features_mock, request_default):
    body = dict(request_default, current_rotation={"seasons": [{"crop_id": "wheat"}, {"crop_id": "chickpea"}]})
    cur = next(s for s in score(features_mock, body)["strategies"] if s["is_current"])
    chick = next(st for st in cur["soil_steps"] if cur["seasons"][st["season_index"]]["crop_id"] == "chickpea")
    assert "n_credit_legume_after_cereal" in chick["rules"] and chick["points"] > 0


def test_allowed_crops_filters_alternatives_but_keeps_current(features_mock, request_default):
    body = dict(request_default, allowed_crops=["wheat", "chickpea"])
    out = score(features_mock, body)
    for s in out["strategies"]:
        if not s["is_current"]:
            assert {x["crop_id"] for x in s["seasons"]} <= {"wheat", "chickpea", "fallow"}, s["id"]
    assert any(s["is_current"] for s in out["strategies"])
    assert "note_allowed_crops" in [n["code"] for n in out["notes"]]


def test_too_few_local_crops_shows_all_alternatives_with_a_note(features_mock, request_default):
    out = score(features_mock, dict(request_default, allowed_crops=["wheat"]))  # was a 500: < 3 strategies
    assert len(out["strategies"]) >= 3
    assert "note_allowed_crops_too_few" in [n["code"] for n in out["notes"]]


def test_without_allowed_crops_nothing_is_filtered(features_mock, request_default):
    assert "note_allowed_crops" not in [n["code"] for n in score(features_mock, request_default)["notes"]]


STEP_SOURCES = {"season_calendar", "water_demand_match", "bare_months_penalty", "family_break"}


def _with_current(request_default, seasons):
    return dict(request_default, current_rotation={"seasons": seasons})


def test_action_steps_follow_the_timeline(features_mock, request_default):
    body = _with_current(request_default, [{"crop_id": "wheat"}, {"crop_id": "fallow"}])
    cur = next(s for s in score(features_mock, body)["strategies"] if s["is_current"])
    actions = [(st["action"], st["crop_id"]) for st in cur["action_steps"]]
    assert actions[0] == ("sow", "wheat")
    assert actions.index(("harvest", "wheat")) < actions.index(("cover_bare", "fallow"))
    sow = next(st for st in cur["action_steps"] if st["action"] == "sow")
    assert sow["months"] == [cur["calendar"][0]["months"][0]["month"]]  # sown at the start of year 1


def test_every_action_step_names_its_source(features_mock, request_default):
    for s in score(features_mock, request_default)["strategies"]:
        assert s["action_steps"], s["id"]
        for st in s["action_steps"]:
            assert st["rule_id"] in STEP_SOURCES, st
            assert st["message"]["code"] in messages.MESSAGES


def test_same_family_twice_gives_an_avoid_step(features_mock, request_default):
    cur = next(s for s in score(features_mock, request_default)["strategies"] if s["is_current"])  # wheat, wheat
    assert any(st["action"] == "avoid" and st["rule_id"] == "family_break" for st in cur["action_steps"])


def test_watch_water_steps_match_dry_months(features_mock, request_default):
    for s in score(features_mock, request_default)["strategies"]:
        dry = sum(1 for row in s["calendar"] for m in row["months"]
                  if any(r["code"] == "stress_water_deficit" for r in m["stress_reasons"]))
        watched = sum(len(st["months"]) for st in s["action_steps"] if st["action"] == "watch_water")
        assert dry == watched, s["id"]


def test_facts_use_faostat_ranges_and_say_when_there_is_none(features_mock, request_default):
    body = _with_current(request_default, [{"crop_id": "wheat"}, {"crop_id": "alfalfa"}])
    cur = next(s for s in score(features_mock, body)["strategies"] if s["is_current"])
    by = {c["crop_id"]: c for c in cur["facts"]["return"]["crops"]}
    assert by["wheat"]["yield_t_per_ha"]["min"] <= by["wheat"]["yield_t_per_ha"]["mean"] <= by["wheat"]["yield_t_per_ha"]["max"]
    assert "FAOSTAT" in by["wheat"]["source"]
    assert by["alfalfa"]["yield_t_per_ha"] is None and by["alfalfa"]["source"] is None
    assert cur["facts"]["return"]["relative_to_current"] == "current"


def test_required_crop_is_in_every_alternative(features_mock, request_default):
    out = score(features_mock, dict(request_default, required_crop="lentil"))
    assert len(out["strategies"]) >= 3
    for s in out["strategies"]:
        if not s["is_current"]:
            assert "lentil" in [x["crop_id"] for x in s["seasons"]], s["id"]
    assert "note_required_crop" in [n["code"] for n in out["notes"]]
