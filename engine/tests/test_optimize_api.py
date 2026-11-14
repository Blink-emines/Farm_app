import copy
import json
import time

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from engine.optimize import optimize
from engine.tests.conftest import REAL_SAMPLE

ENG = __import__("pathlib").Path(__file__).resolve().parents[1]
CONTRACTS = ENG.parent / "docs" / "contracts"


def _validators():
    strat = json.loads((CONTRACTS / "strategy.schema.json").read_text())
    opt = json.loads((ENG / "optimize.schema.draft.json").read_text())
    reg = Registry().with_resource(strat["$id"], Resource.from_contents(strat))
    resp = Draft202012Validator({"$schema": opt["$schema"], "$defs": opt["$defs"], "$ref": "#/$defs/OptimizeResponse"}, registry=reg)
    req = Draft202012Validator({"$schema": opt["$schema"], "$defs": opt["$defs"], "$ref": "#/$defs/OptimizeRequest"}, registry=reg)
    return req, resp


def _request(n=2, **extra):
    r = {"latitude": 33.96, "longitude": -5.27, "profile": "balanced",
         "parcels": [{"id": f"p{i+1}", "area_ha": 2.0 + i,
                      "current_rotation": {"seasons": [{"crop_id": "wheat"}, {"crop_id": "fallow"}]}}
                     for i in range(n)]}
    r.update(extra)
    return r


@pytest.fixture(scope="module")
def real():
    return json.loads(REAL_SAMPLE.read_text())


def test_request_and_response_validate_on_mock(features_mock):
    req_v, resp_v = _validators()
    req = _request()
    assert req_v.is_valid(req)
    out = optimize(features_mock, req)
    errs = list(resp_v.iter_errors(out))
    assert not errs, errs[0].message + str(list(errs[0].path))
    assert out["solver"]["status"] in ("optimal", "feasible")
    assert [p["id"] for p in out["parcels"]] == ["p1", "p2"]


def test_response_validates_on_real_sample(real):
    _, resp_v = _validators()
    out = optimize(real, _request())
    assert resp_v.is_valid(out)


def test_plan_explained_by_rules_and_has_baseline(features_mock):
    out = optimize(features_mock, _request(1))
    p = out["parcels"][0]
    assert p["plan"]["why"] and p["baseline"]["is_current"] and not p["plan"]["is_current"]
    assert any(e["feature"] == "economics.revenue_range" for e in p["plan"]["evidence"])
    codes = {g["code"] for g in p["plan"]["information_gaps"]}
    assert {"gap_local_prices", "gap_costs_unknown", "gap_yield_national"} <= codes


def test_profiles_shift_the_plan(real):
    inc = optimize(real, _request(1, profile="economic"))["parcels"][0]["plan"]["score"]["by_priority"]
    eco = optimize(real, _request(1, profile="ecological"))["parcels"][0]["plan"]["score"]["by_priority"]
    assert inc["extra_income"] >= eco["extra_income"]
    assert eco["improve_soil"] >= inc["improve_soil"]


def test_priorities_instead_of_profile(features_mock):
    req = _request(1)
    del req["profile"]
    req["priorities"] = {"save_water": 5, "improve_soil": 0, "extra_income": 0, "reduce_erosion": 0, "forage": 0}
    assert _validators()[0].is_valid(req)
    assert optimize(features_mock, req)["solver"]["status"] in ("optimal", "feasible")


def test_water_cap_changes_totals(real):
    free = optimize(real, _request(2))
    capped = optimize(real, _request(2, water={"monthly_irrigation_m3": [0] * 12}))
    assert capped["totals"]["irrigation_need_m3_per_year"] <= 1e-6
    assert capped["totals"]["gross_revenue_mad_per_year"] <= free["totals"]["gross_revenue_mad_per_year"] + 1e-6


def test_cost_override_gives_profit(features_mock):
    req = _request(1, price_overrides={"wheat": {"cost_mad_per_ha": 3000}})
    out = optimize(features_mock, req)
    assert out["totals"]["profit_mad_per_year"] is not None
    assert optimize(features_mock, _request(1))["totals"]["profit_mad_per_year"] is None


def test_pareto_points_returned_and_ordered(real):
    out = optimize(real, _request(1, pareto_points=5))
    pts = out["pareto"]
    assert 2 <= len(pts) <= 5
    inc = [p["revenue_mad_per_ha_year"] for p in pts]
    assert inc == sorted(inc)


def test_invalid_request_rejected(features_mock):
    bad = _request()
    bad["parcels"][0]["area_ha"] = -1
    with pytest.raises(ValueError):
        optimize(features_mock, bad)


def test_solve_time_five_parcels_with_pareto(real):
    t = time.time()
    out = optimize(real, _request(5, pareto_points=6))
    elapsed = time.time() - t
    assert out["solver"]["status"] in ("optimal", "feasible")
    assert elapsed < 3.0, elapsed


def test_optimiser_messages_registered(features_mock):
    from engine import messages
    out = optimize(features_mock, _request(1, pareto_points=3))
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


def _parcel(pid, area, irrigated=None, seasons=None):
    p = {"id": pid, "area_ha": area,
         "current_rotation": {"seasons": seasons or [{"crop_id": "wheat"}, {"crop_id": "fallow"}]}}
    if irrigated is not None:
        p["irrigated"] = irrigated
    return p


def _crops_of(parcel_result):
    return [s["crop_id"] for s in parcel_result["plan"]["seasons"]]


def test_rainfed_default_excludes_irrigation_crops_and_irrigated_allows_them(real):
    req = _request(1, profile="economic")
    req["parcels"] = [_parcel("rain", 2.0), _parcel("irr", 2.0, irrigated=True)]
    out = optimize(real, req)
    rain, irr = out["parcels"]
    assert rain["irrigated"] is False and irr["irrigated"] is True
    assert "potato" not in _crops_of(rain)
    assert "potato" in _crops_of(irr)  # the economic profile picks potato when irrigation is allowed


def test_no_parcel_repeats_potato_within_24_months(real):
    for profile in ("economic", "balanced", "ecological"):
        req = _request(1, profile=profile)
        req["parcels"] = [_parcel("irr", 2.0, irrigated=True)]
        crops = _crops_of(optimize(real, req)["parcels"][0])
        assert crops.count("potato") <= 1, (profile, crops)


def test_family_gap_limits_other_families(real):
    req = _request(1, profile="economic")
    req["parcels"] = [_parcel("irr", 2.0, irrigated=True)]
    crops = _crops_of(optimize(real, req)["parcels"][0])
    assert sum(c in ("chickpea", "lentil", "faba_bean", "vetch_oat_cover") for c in crops) <= 1  # fabaceae once per cycle
    assert crops.count("sunflower") <= 1


def test_water_cap_only_binds_irrigated_parcels(real):
    req = _request(1, water={"monthly_irrigation_m3": [0] * 12})
    req["parcels"] = [_parcel("rain", 2.0), _parcel("irr", 3.0, irrigated=True)]
    out = optimize(real, req)
    rain, irr = out["parcels"]
    assert any(c != "fallow" for c in _crops_of(rain))      # rainfed parcel is not capped
    assert set(_crops_of(irr)) == {"fallow"}                  # irrigated parcel has no water
    assert out["totals"]["irrigation_need_m3_per_year"] <= 1e-6


def test_insufficient_irrigation_is_said_clearly(real):
    req = _request(1, water={"monthly_irrigation_m3": [0] * 12})
    req["parcels"] = [_parcel("irr", 3.0, irrigated=True)]
    out = optimize(real, req)
    assert any(g["code"] == "gap_irrigation_insufficient" for g in out["information_gaps"])
    assert any(g["code"] == "gap_irrigation_insufficient" for g in out["parcels"][0]["plan"]["information_gaps"])
    # no message when the parcel is rainfed (the cap does not apply to it)
    req["parcels"] = [_parcel("rain", 3.0)]
    out = optimize(real, req)
    assert not any(g["code"] == "gap_irrigation_insufficient" for g in out["information_gaps"])


def test_national_yield_gap_mentions_mixed_irrigation(real):
    out = optimize(real, _request(1))
    g = next(g for g in out["parcels"][0]["plan"]["information_gaps"] if g["code"] == "gap_yield_national")
    assert "irrigated and rainfed" in g["default_text"]


def test_crops_yaml_irrigation_required_is_labelled():
    from engine.loaders import load_crops
    crops = load_crops()
    assert crops["potato"]["irrigation_required"]["value"] is True
    assert all(c["irrigation_required"]["source"] for c in crops.values())
