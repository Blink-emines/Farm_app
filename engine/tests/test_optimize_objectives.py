import pytest

from engine import rules
from engine.optimize.objectives import (build_tables, load_economics, plan_values, plan_from_crops)
from engine.loaders import UNKNOWN


@pytest.fixture
def econ():
    return load_economics()


@pytest.fixture
def tables(features_mock, crops, weights, econ):
    return build_tables(features_mock, crops, weights, econ)


def test_economics_every_number_has_source_and_year(econ):
    for cid, c in econ["crops"].items():
        for key in ("price_mad_per_t", "cost_mad_per_ha"):
            assert c[key]["source"], (cid, key)
        assert c["yield_t_per_ha"]["source"]
        p = c["price_mad_per_t"]["value"]
        if isinstance(p, (int, float)) and cid != "fallow":
            assert "2024" in c["price_mad_per_t"]["source"]
            y = c["yield_t_per_ha"]
            assert y["min"] <= y["mean"] <= y["max"]
            assert "2015-2024" in y["source"]
            assert c["price_mad_per_t"]["editable"] == "editable default"


def test_costs_are_unknown_not_invented(econ):
    assert all(c["cost_mad_per_ha"]["value"] == UNKNOWN for c in econ["crops"].values())


def test_unpriced_crops(econ):
    for cid in ("alfalfa", "vetch_oat_cover"):
        assert econ["crops"][cid]["price_mad_per_t"]["value"] == UNKNOWN


def test_fallow_has_zero_water_demand(tables):
    assert all(v == 0 for v in tables.deficit["fallow"])


def test_vetch_oat_uses_proxy_kc_so_water_is_not_zero(tables):
    assert sum(tables.deficit["vetch_oat_cover"]) > 0


def test_deficit_is_kc_et0_minus_rain(tables, features_mock, crops):
    m = features_mock["climate"]["monthly"]
    kc = crops["wheat"]["kc_mid"]["value"]
    for t in range(12):
        expect = max(0.0, kc * m["et0"]["values"][t] - m["precipitation"]["values"][t])
        assert tables.deficit["wheat"][t] == pytest.approx(expect)


def test_plan_values_improve_soil_equals_rule_points(tables, make_ctx, crops, features_mock, weights):
    plan = plan_from_crops(["wheat", "chickpea"], crops)
    v = plan_values(plan, tables, crops, features_mock, weights)
    ctx = make_ctx(["wheat", "chickpea"])
    pts = sum(w["points"] for r in (rules.n_credit_legume_after_cereal, rules.family_break, rules.deep_root_structure)
              for w in r(ctx).why)
    assert v["u"]["improve_soil"] == pytest.approx(pts)


def test_plan_values_revenue(tables, crops, features_mock, weights, econ):
    plan = plan_from_crops(["wheat", "chickpea"], crops)
    v = plan_values(plan, tables, crops, features_mock, weights)
    e = econ["crops"]
    expect = sum(e[c]["price_mad_per_t"]["value"] * e[c]["yield_t_per_ha"]["mean"] for c in ("wheat", "chickpea")) / 2
    assert v["revenue_avg"] == pytest.approx(expect)
    assert v["revenue_bad"] < v["revenue_avg"] < v["revenue_good"]


def test_profit_only_when_costs_given(features_mock, crops, weights, econ):
    plan = plan_from_crops(["wheat", "chickpea"], crops)
    t0 = build_tables(features_mock, crops, weights, econ)
    assert plan_values(plan, t0, crops, features_mock, weights)["profit_avg"] is None
    t1 = build_tables(features_mock, crops, weights, econ,
                      overrides={"wheat": {"cost_mad_per_ha": 1000}, "chickpea": {"cost_mad_per_ha": 500}})
    v = plan_values(plan, t1, crops, features_mock, weights)
    assert v["profit_avg"] == pytest.approx(v["revenue_avg"] - (1000 + 500) / 2)
    assert t1.income_mode == "profit" and t0.income_mode == "gross_revenue"


def test_price_override(features_mock, crops, weights, econ):
    t = build_tables(features_mock, crops, weights, econ, overrides={"wheat": {"price_mad_per_t": 1.0}})
    assert t.rev_avg["wheat"] == pytest.approx(econ["crops"]["wheat"]["yield_t_per_ha"]["mean"])
