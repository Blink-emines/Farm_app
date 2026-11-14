"""One test per rule: sign, priority and that the why entry is emitted (not exact points)."""
from engine import rules


def test_n_credit_legume_after_cereal(make_ctx):
    r = rules.n_credit_legume_after_cereal(make_ctx(["wheat", "chickpea"]))
    assert len(r.why) == 1 and r.why[0]["effect"] == "bonus" and r.why[0]["priority"] == "improve_soil"
    assert rules.n_credit_legume_after_cereal(make_ctx(["wheat", "barley"])).why == []


def test_family_break(make_ctx):
    good = rules.family_break(make_ctx(["wheat", "chickpea"]))
    assert good.why and all(w["effect"] == "bonus" and w["priority"] == "improve_soil" for w in good.why)
    bad = rules.family_break(make_ctx(["wheat", "wheat"]))
    assert bad.why and all(w["effect"] == "penalty" for w in bad.why)
    assert rules.family_break(make_ctx(["alfalfa"])).why == []  # perennial staying put


def test_family_break_vetch_oat_counts_as_fabaceae(make_ctx):
    r = rules.family_break(make_ctx(["wheat", "vetch_oat_cover"]))
    assert all(w["effect"] == "bonus" for w in r.why)  # user decision: no same-family penalty


def test_deep_root_structure(make_ctx):
    r = rules.deep_root_structure(make_ctx(["wheat", "chickpea"]))
    assert r.why[0]["effect"] == "bonus" and r.why[0]["priority"] == "improve_soil"
    assert rules.deep_root_structure(make_ctx(["potato"])).why == []


def test_deep_root_unknown_is_a_gap(make_ctx):
    r = rules.deep_root_structure(make_ctx(["vetch_oat_cover"]))
    assert r.why == [] and r.gaps[0]["code"] == "gap_rooting_unknown"


def test_bare_months_penalty(make_ctx):
    r = rules.bare_months_penalty(make_ctx(["wheat"]))
    assert r.why[0]["effect"] == "penalty" and r.why[0]["priority"] == "reduce_erosion"
    assert rules.bare_months_penalty(make_ctx(["olive_intercrop"])).why == []


def test_cover_fills_bare(make_ctx):
    r = rules.cover_fills_bare(make_ctx(["wheat", "vetch_oat_cover"]))
    assert r.why[0]["effect"] == "bonus" and r.why[0]["priority"] == "reduce_erosion"
    assert rules.cover_fills_bare(make_ctx(["wheat", "chickpea"])).why == []


def test_water_demand_match(make_ctx):
    r = rules.water_demand_match(make_ctx(["wheat", "sunflower"]))
    effects = {w["effect"] for w in r.why}
    assert effects == {"bonus", "penalty"} and {w["priority"] for w in r.why} == {"save_water"}
    assert r.evidence


def test_water_vetch_oat_uses_proxy_kc_and_says_so(make_ctx):
    r = rules.water_demand_match(make_ctx(["vetch_oat_cover"]))
    assert r.why and any(g["code"] == "gap_kc_proxy" for g in r.gaps)


def test_water_unknown_kc_is_a_gap(make_ctx):
    ctx = make_ctx(["wheat"])
    ctx.crops["wheat"]["kc_mid"]["value"] = "unknown, needs local data"
    r = rules.water_demand_match(ctx)
    assert r.why == [] and any(g["code"] == "gap_kc_unknown" for g in r.gaps)


def test_income_flag(make_ctx):
    r = rules.income_flag(make_ctx(["potato"]))
    assert r.why[0]["effect"] == "bonus" and r.why[0]["priority"] == "extra_income"
    assert rules.income_flag(make_ctx(["barley"])).why[0]["effect"] == "neutral"


def test_forage_flag(make_ctx):
    r = rules.forage_flag(make_ctx(["alfalfa"]))
    assert r.why[0]["effect"] == "bonus" and r.why[0]["priority"] == "forage"


def test_rule_points_come_from_weights(make_ctx):
    ctx = make_ctx(["wheat", "chickpea"])
    ctx.weights["rules"]["n_credit_legume_after_cereal"]["points_per_transition"] = 100
    assert rules.n_credit_legume_after_cereal(ctx).why[0]["points"] == 50  # 100 / 2 years
