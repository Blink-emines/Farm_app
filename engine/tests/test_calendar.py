from engine.season_calendar import layout
from engine.templates import TEMPLATES


def _flat(ctx):
    return [c for row in ctx.calendar for c in row["months"]]


def test_twelve_months_per_year(make_ctx):
    ctx = make_ctx(["wheat", "chickpea"])
    assert len(ctx.calendar) == 2 and all(len(r["months"]) == 12 for r in ctx.calendar)


def test_crop_wraps_across_new_year(make_ctx):
    ctx = make_ctx(["wheat", "chickpea"])  # wheat sown in autumn of year 1 grows into year 2
    assert ctx.calendar[1]["months"][0]["crop_id"] == "wheat"


def test_bare_months_detected(make_ctx):
    assert any(c["status"] == "bare" and c["crop_id"] is None for c in _flat(make_ctx(["wheat"])))


def test_fallow_is_bare_but_named(make_ctx):
    row = make_ctx(["wheat", "fallow"]).calendar[1]["months"]
    assert all(c["status"] == "bare" and c["crop_id"] == "fallow" for c in row[6:])


def test_water_stress_month(make_ctx):
    ctx = make_ctx(["sunflower"])  # grows through the dry summer in the mock climate
    stressed = [c for c in _flat(ctx) if c["status"] == "stress"]
    assert stressed and any(r["code"] == "stress_water_deficit" for c in stressed for r in c["stress_reasons"])


def test_generic_frost_warning(make_ctx):
    ctx = make_ctx(["wheat"])  # mock has 4 frost days in January
    reasons = [r for c in _flat(ctx) for r in c["stress_reasons"] if r["code"] == "stress_frost_generic"]
    assert reasons and "generic level, not crop-specific" in reasons[0]["default_text"]


def test_generic_heat_warning(make_ctx):
    ctx = make_ctx(["sunflower"])
    reasons = [r for c in _flat(ctx) for r in c["stress_reasons"] if r["code"] == "stress_heat_generic"]
    assert reasons and "generic level, not crop-specific" in reasons[0]["default_text"]


def _count(ctx):
    cells = _flat(ctx)
    return (sum(c["status"] in ("growing", "stress") for c in cells),
            sum(c["status"] == "bare" for c in cells))


def _ribbon(ctx, row):
    sym = {"growing": "G", "stress": "S", "bare": "."}
    return "".join(sym[c["status"]] for c in ctx.calendar[row]["months"])


def _crop_months(ctx, crop):
    return [(r["year"], c["month"]) for r in ctx.calendar for c in r["months"] if c["crop_id"] == crop]


def test_wheat_fallow_cycle(make_ctx):
    ctx = make_ctx(["wheat", "fallow"])
    assert len(ctx.calendar) == 2
    assert _count(ctx) == (8, 16)
    assert sorted(m for _, m in _crop_months(ctx, "wheat")) == [1, 2, 3, 4, 5, 6, 11, 12]
    assert len(_crop_months(ctx, "fallow")) == 12


def test_wheat_chickpea_march_after_wheat_harvest(make_ctx):
    ctx = make_ctx(["wheat", "chickpea"])
    sp = {s["crop_id"]: s for s in ctx.seasons}
    assert sp["chickpea"]["sow_month"] == 3
    # steady state: sown in the first March after the wheat harvest (row 1 is filled by the previous cycle)
    assert _crop_months(ctx, "chickpea") == [(1, m) for m in (3, 4, 5, 6, 7)]
    assert [m for y, m in _crop_months(ctx, "wheat") if y == 1] == [11, 12]
    assert [m for y, m in _crop_months(ctx, "wheat") if y == 2] == [1, 2, 3, 4, 5, 6]


def test_wheat_chickpea_no_month_has_two_crops(make_ctx):
    ctx = make_ctx(["wheat", "chickpea"])
    wheat, chick = set(_crop_months(ctx, "wheat")), set(_crop_months(ctx, "chickpea"))
    assert wheat and chick and not (wheat & chick)


def test_barley_lentil(make_ctx):
    ctx = make_ctx(["barley", "lentil"])  # barley 11-5, lentil 11-5
    assert len(ctx.calendar) == 2
    assert not (set(_crop_months(ctx, "barley")) & set(_crop_months(ctx, "lentil")))
    g, b = _count(ctx)
    assert g == 14 and b == 10  # 7 + 7 growing months in 24


def test_perennial_only_rotation(make_ctx):
    for crop in ("alfalfa", "olive_intercrop"):
        ctx = make_ctx([crop])
        assert len(ctx.calendar) == 1
        assert all(c["crop_id"] == crop and c["status"] != "bare" for c in ctx.calendar[0]["months"])


def test_rows_start_in_january(make_ctx):
    for row in make_ctx(["wheat", "chickpea"]).calendar:
        assert [c["month"] for c in row["months"]] == list(range(1, 13))


def _all_layouts(crops, weights):
    from engine.scorer import resolve_seasons
    ids = [t["crops"] for t in TEMPLATES] + [["wheat", "wheat"], ["wheat", "fallow", "fallow"],
                                             ["fallow", "wheat"], ["alfalfa", "wheat"],
                                             ["potato", "wheat", "chickpea"], ["fallow"]]
    for crop_ids in ids:
        seasons, _ = resolve_seasons(crop_ids, None, crops)
        yield crop_ids, layout(seasons, crops)


def test_property_seasons_never_overlap(crops, weights):
    for crop_ids, lay in _all_layouts(crops, weights):
        spans = lay["spans"]
        for (a0, a1, _), (b0, b1, _) in zip(spans, spans[1:]):
            assert b0 > a1, crop_ids
        assert spans[-1][1] < spans[0][0] + lay["length"], crop_ids  # next cycle starts after the last harvest
        assert lay["length"] % 12 == 0
        occupied = sum(1 for x in lay["slots"] if x is not None)
        assert occupied == sum(e - s + 1 for s, e, _ in spans), crop_ids
