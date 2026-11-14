"""Scoring rules. One named function per rule; each returns a Result.
Points come only from weights.yaml (ctx.w). Points are per event / n_years."""
from dataclasses import dataclass, field

from .loaders import families, field as crop_field, is_unknown, rooting_class, val
from .messages import msg
from .season_calendar import water_need_mm


@dataclass
class Ctx:
    seasons: list      # [{crop_id, sow_month, harvest_month}]
    calendar: list
    crops: dict
    features: dict
    weights: dict      # whole weights.yaml
    source_names: dict # features source id -> name

    @property
    def ids(self):
        return [s["crop_id"] for s in self.seasons]

    @property
    def n_years(self):
        return len(self.calendar)  # calendar years in one cycle of the rotation

    def w(self, rule_id):
        return self.weights["rules"][rule_id]

    def months(self):
        return [(row["year"], c) for row in self.calendar for c in row["months"]]


@dataclass
class Result:
    why: list = field(default_factory=list)
    gaps: list = field(default_factory=list)
    evidence: list = field(default_factory=list)


def _why(rule_id, w, points, message):
    points = round(points, 2)
    effect = "bonus" if points > 0 else "penalty" if points < 0 else "neutral"
    return {"rule_id": rule_id, "effect": effect, "points": points,
            "priority": w["priority"], "message": message}


def _crop_evidence(ctx, crop, name, unit, source=None):
    e = crop_field(ctx.crops, crop, name)
    v = e["value"]
    if isinstance(v, bool):
        v = "yes" if v else "no"
    elif isinstance(v, list):
        v = ",".join(v)
    return {"feature": f"crops.{crop}.{name}", "value": v, "unit": unit,
            "source": source or e["source"]}


def _months_str(ms):
    return ",".join(str(m) for m in sorted(set(ms)))


def n_credit_legume_after_cereal(ctx):
    w, res, ids = ctx.w("n_credit_legume_after_cereal"), Result(), ctx.ids
    for i, cur in enumerate(ids):
        prev = ids[i - 1]  # cyclic: the rotation repeats
        if val(ctx.crops, prev, "cereal") and val(ctx.crops, cur, "legume"):
            res.why.append(_why("n_credit_legume_after_cereal", w,
                                w["points_per_transition"] / ctx.n_years,
                                msg("n_credit_applied", from_crop=prev, to_crop=cur)))
            res.evidence.append(_crop_evidence(ctx, cur, "legume", "yes/no"))
    return res


def family_break(ctx):
    w, res, ids = ctx.w("family_break"), Result(), ctx.ids
    for i, cur in enumerate(ids):
        prev = ids[i - 1]
        fp, fc = families(ctx.crops, prev), families(ctx.crops, cur)
        if not fp or not fc:
            continue  # fallow: no family, neither bonus nor penalty
        if prev == cur and val(ctx.crops, cur, "perennial"):
            continue  # a perennial staying put is not a repeated sowing
        if fp & fc:
            res.why.append(_why("family_break", w, w["points_per_same_family_repeat"] / ctx.n_years,
                                msg("family_repeat", from_crop=prev, to_crop=cur)))
        else:
            res.why.append(_why("family_break", w, w["points_per_family_change"] / ctx.n_years,
                                msg("family_change", from_crop=prev, to_crop=cur)))
        res.evidence.append(_crop_evidence(ctx, cur, "family", "taxon"))
    return res


def deep_root_structure(ctx):
    w, res = ctx.w("deep_root_structure"), Result()
    deep, unknown = [], []
    for c in ctx.ids:
        if c == "fallow":
            continue
        cls = rooting_class(ctx.crops, c, ctx.weights)
        if cls is None:
            unknown.append(c)
        elif cls == "deep":
            deep.append(c)
            res.evidence.append(_crop_evidence(ctx, c, "rooting_zr_min_m", "m"))
    if deep:
        res.why.append(_why("deep_root_structure", w, w["points_per_deep_crop_year"] * len(deep) / ctx.n_years,
                            msg("deep_root_present", crops=",".join(sorted(set(deep))), years=len(deep))))
    if unknown:
        res.gaps.append(msg("gap_rooting_unknown", crops=",".join(sorted(set(unknown)))))
    return res


def bare_months_penalty(ctx):
    w, res = ctx.w("bare_months_penalty"), Result()
    bare = [c["month"] for _, c in ctx.months() if c["status"] == "bare"]
    if bare:
        res.why.append(_why("bare_months_penalty", w, w["points_per_bare_month"] * len(bare) / ctx.n_years,
                            msg("bare_months", count=len(bare), months=_months_str(bare))))
    return res


def cover_fills_bare(ctx):
    w, res = ctx.w("cover_fills_bare"), Result()
    for crop in sorted({c for c in ctx.ids if val(ctx.crops, c, "cover")}):
        n = sum(1 for _, c in ctx.months() if c["crop_id"] == crop)
        res.why.append(_why("cover_fills_bare", w, w["points_per_cover_month"] * n / ctx.n_years,
                            msg("cover_crop_months", crop=crop, count=n)))
        res.evidence.append(_crop_evidence(ctx, crop, "cover", "yes/no"))
    return res


def water_demand_match(ctx):
    """Crop need (FAO-56 Kc_mid x et0) vs rainfall in each growing month."""
    w, res = ctx.w("water_demand_match"), Result()
    ok = stress = 0
    stress_months, no_kc, missing = [], set(), set()
    for _, c in ctx.months():
        crop = c["crop_id"]
        if crop is None or crop == "fallow":
            continue
        m = c["month"]
        need = water_need_mm(ctx.crops, crop, ctx.features, m)
        rain = ctx.features["climate"]["monthly"]["precipitation"]["values"][m - 1]
        if not isinstance(val(ctx.crops, crop, "kc_mid"), (int, float)):
            no_kc.add(crop)
        elif need is None or rain is None:
            missing.add(m)
        elif need > rain:
            stress += 1
            stress_months.append(m)
        else:
            ok += 1
    n = ctx.n_years
    if ok:
        res.why.append(_why("water_demand_match", w, w["points_per_ok_month"] * ok / n,
                            msg("water_ok_months", count=ok)))
    if stress:
        res.why.append(_why("water_demand_match", w, w["points_per_stress_month"] * stress / n,
                            msg("water_stress_months", count=stress)))
    if no_kc:
        res.gaps.append(msg("gap_kc_unknown", crops=",".join(sorted(no_kc))))
    if missing:
        res.gaps.append(msg("gap_climate_month_missing", months=_months_str(missing)))
    src = ctx.source_names
    for name in ("precipitation", "et0"):
        s = ctx.features["climate"]["monthly"][name]
        res.evidence.append({"feature": f"climate.monthly.{name}", "value": s["values"],
                             "unit": s["unit"], "source": src.get(s["source"], s["source"])})
    for crop in sorted({c for c in ctx.ids if c != "fallow"}):
        res.evidence.append(_crop_evidence(ctx, crop, "kc_mid", "FAO-56 Kc (-)"))
    return res


def _flag_rule(ctx, rule_id, flag, code):
    w, res = ctx.w(rule_id), Result()
    pts, levels, unknown = 0, [], []
    for c in ctx.ids:
        lvl = val(ctx.crops, c, flag)
        if lvl not in w["points_by_level"]:
            unknown.append(c)
            continue
        pts += w["points_by_level"][lvl]
        levels.append(f"{c}:{lvl}")
        res.evidence.append(_crop_evidence(ctx, c, flag, "qualitative"))
    res.why.append(_why(rule_id, w, pts / ctx.n_years, msg(code, levels=",".join(levels) or "none")))
    if unknown:
        res.gaps.append(msg("gap_flag_unknown", crops=",".join(sorted(set(unknown))), flag=flag))
    return res


def income_flag(ctx):
    return _flag_rule(ctx, "income_flag", "income_flag", "income_flag_points")


def forage_flag(ctx):
    return _flag_rule(ctx, "forage_flag", "forage_flag", "forage_flag_points")


RULES = [n_credit_legume_after_cereal, family_break, deep_root_structure, bare_months_penalty,
         cover_fills_bare, water_demand_match, income_flag, forage_flag]
