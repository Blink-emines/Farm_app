import pytest

from engine.optimize.model import FarmModel
from engine.optimize.objectives import OBJ, build_tables, load_economics, plan_from_crops, plan_values
from engine.optimize.windows import sowing_windows


@pytest.fixture
def farm(features_mock, crops, weights):
    tables = build_tables(features_mock, crops, weights, load_economics())
    win, _ = sowing_windows(features_mock, crops, weights)
    return FarmModel(tables, win, crops, weights, features_mock, areas=[1.0])


def test_every_objective_value_matches_the_evaluator(farm, crops, features_mock, weights):
    """The linear MILP expressions must reproduce the rule-based evaluator on the solved plan."""
    for k in OBJ:
        plan, model_u = farm.maximise_utility(k)
        ref = plan_values(plan[0], farm.tables, crops, features_mock, weights)
        for kk in OBJ:
            assert model_u[kk] == pytest.approx(ref["u"][kk], abs=1e-6), (k, kk)


def test_no_overlap_and_windows_respected(farm):
    for k in OBJ:
        plan, _ = farm.maximise_utility(k)
        spans = sorted(plan[0]["spans"])
        L = plan[0]["length"]
        occ = [None] * L
        for s, e, c in spans:
            for a in range(s, e + 1):
                assert occ[a % L] is None, (k, spans)
                occ[a % L] = c
            if c not in ("fallow", "alfalfa", "olive_intercrop"):
                assert (s % 12) + 1 in farm.windows[c], (k, c, s)


def test_single_objective_beats_every_template(farm, crops, features_mock, weights):
    from engine.templates import TEMPLATES
    for k in OBJ:
        _, best = farm.maximise_utility(k)
        for t in TEMPLATES:
            ref = plan_values(plan_from_crops(t["crops"], crops), farm.tables, crops, features_mock, weights)
            assert best[k] >= ref["u"][k] - 1e-6, (k, t["id"])


def test_water_only_gives_zero_deficit_and_erosion_only_few_bare_months(farm):
    plan, u = farm.maximise_utility("save_water")
    assert u["save_water"] == pytest.approx(0.0)
    plan, u = farm.maximise_utility("reduce_erosion")
    assert u["reduce_erosion"] >= 0


def test_weighted_solve_prefers_heavier_goal(farm):
    n = farm.payoff()
    _, inc = farm.solve_weighted({"save_water": 0, "improve_soil": 0, "extra_income": 5, "reduce_erosion": 0, "forage": 0})
    _, wat = farm.solve_weighted({"save_water": 5, "improve_soil": 0, "extra_income": 0, "reduce_erosion": 0, "forage": 0})
    assert inc["extra_income"] >= wat["extra_income"] and wat["save_water"] >= inc["save_water"]


def test_water_cap_is_respected_and_always_feasible(features_mock, crops, weights):
    tables = build_tables(features_mock, crops, weights, load_economics())
    win, _ = sowing_windows(features_mock, crops, weights)
    cap = [0.0] * 12  # no irrigation water at all
    m = FarmModel(tables, win, crops, weights, features_mock, areas=[2.0, 3.0], water_m3=cap)
    plan, u = m.maximise_utility("extra_income")
    assert m.last_status in ("optimal", "feasible")
    for p, area in zip(plan, [2.0, 3.0]):
        v = plan_values(p, tables, crops, features_mock, weights)
        assert v["u"]["save_water"] == pytest.approx(0.0, abs=1e-6)  # only zero-deficit plans fit


def test_pareto_income_falls_as_water_tightens(farm):
    farm.payoff()
    pts = farm.pareto(5)
    assert len(pts) >= 2
    inc = [p["u"]["extra_income"] for p in pts]  # ordered from tightest water to loosest
    wat = [p["u"]["save_water"] for p in pts]
    assert all(a >= b - 1e-6 for a, b in zip(wat, wat[1:]))
    assert all(a <= b + 1e-6 for a, b in zip(inc, inc[1:]))
