"""Objective data (crop tables) and the rule-based evaluator for any plan.

A plan is {"length": L, "spans": [(start, end, crop_id)]} on a cyclic axis of L months
(absolute index 0 = January of calendar row 1). All objectives are "utilities" to MAXIMISE,
per hectare and per year:
  save_water      = - sum over growing months of max(0, Kc_mid x ET0 - precipitation)  (mm)
  improve_soil    = rule points (n_credit_legume_after_cereal, family_break, deep_root_structure)
  extra_income    = gross revenue (price x mean yield), or profit when costs are given (MAD)
  reduce_erosion  = rule points (bare_months_penalty, cover_fills_bare)
  forage          = rule points (forage_flag)
Fallow has no crop transpiration, so its water deficit is 0 (bare-soil evaporation is ignored)."""
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ..loaders import UNKNOWN, field as crop_field, val
from ..rules import (Ctx, bare_months_penalty, cover_fills_bare, deep_root_structure, family_break,
                     forage_flag, n_credit_legume_after_cereal)
from ..season_calendar import calendar_from_spans, layout

OBJ = ["save_water", "improve_soil", "extra_income", "reduce_erosion", "forage"]
_RULES = [n_credit_legume_after_cereal, family_break, deep_root_structure,
          bare_months_penalty, cover_fills_bare, forage_flag]


def load_economics():
    return yaml.safe_load((Path(__file__).resolve().parent.parent / "economics.yaml").read_text())


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


@dataclass
class Tables:
    horizon: int
    duration: dict          # crop -> months occupied per sowing
    deficit: dict           # crop -> 12 monthly water deficits (mm)
    excluded: list          # crops without a usable Kc (shown, never optimised)
    rev_bad: dict
    rev_avg: dict
    rev_good: dict          # per sowing of an annual crop; None = no price/yield data
    cost: dict              # per sowing; None = unknown
    income_mode: str        # "gross_revenue" or "profit"
    unpriced: list = field(default_factory=list)
    costless: list = field(default_factory=list)


def build_tables(features, crops, weights, econ, overrides=None):
    overrides = overrides or {}
    horizon = weights["optimiser"]["horizon_months"]
    m = features["climate"]["monthly"]
    et0, rain = m["et0"]["values"], m["precipitation"]["values"]
    duration, deficit, excluded = {}, {}, []
    rev = {"bad": {}, "avg": {}, "good": {}}
    cost, unpriced, costless = {}, [], []
    for cid in crops:
        if cid == "fallow":
            duration[cid], deficit[cid] = 12, [0.0] * 12
        else:
            if val(crops, cid, "perennial"):
                duration[cid] = horizon
            else:
                s, h = val(crops, cid, "sow_month"), val(crops, cid, "harvest_month")
                duration[cid] = (h - s) % 12 + 1
            kc = val(crops, cid, "kc_mid")
            if _num(kc) and all(_num(v) for v in et0 + rain):
                deficit[cid] = [max(0.0, kc * e - r) for e, r in zip(et0, rain)]
            else:
                deficit[cid] = [0.0] * 12
                excluded.append(cid)
        e, o = econ["crops"][cid], overrides.get(cid, {})
        price = o.get("price_mad_per_t", e["price_mad_per_t"]["value"])
        y = e["yield_t_per_ha"]
        ymean = o.get("yield_t_per_ha", y["mean"])
        if _num(price) and _num(ymean) and cid != "fallow":
            f = ymean / y["mean"] if _num(y["mean"]) and y["mean"] else 1.0
            ymin = y["min"] * f if _num(y["min"]) else ymean
            ymax = y["max"] * f if _num(y["max"]) else ymean
            rev["bad"][cid], rev["avg"][cid], rev["good"][cid] = price * ymin, price * ymean, price * ymax
        else:
            for k in rev:
                rev[k][cid] = None
            if cid != "fallow":
                unpriced.append(cid)
        c = o.get("cost_mad_per_ha", e["cost_mad_per_ha"]["value"])
        cost[cid] = c if _num(c) else None
        if cost[cid] is None and cid != "fallow":
            costless.append(cid)
    mode = "profit" if any(_num(v) for v in cost.values()) else "gross_revenue"
    return Tables(horizon, duration, deficit, excluded, rev["bad"], rev["avg"], rev["good"], cost,
                  mode, unpriced, costless)


def income_per_sowing(tables, cid, kind="avg"):
    """MAD per ha for ONE sowing of an annual crop (perennials: multiply by years occupied)."""
    return {"bad": tables.rev_bad, "avg": tables.rev_avg, "good": tables.rev_good}[kind][cid] or 0.0


def objective_income_per_sowing(tables, cid):
    """What the extra_income objective earns per sowing: revenue, minus cost when costs are given."""
    r = income_per_sowing(tables, cid)
    return r - (tables.cost[cid] or 0.0) if tables.income_mode == "profit" else r


def plan_from_crops(crop_ids, crops, request_seasons=None):
    """A plan from a crop sequence, with the layout rule (approved default months unless given)."""
    from ..scorer import resolve_seasons
    seasons, _ = resolve_seasons(crop_ids, request_seasons, crops)
    lay = layout(seasons, crops)
    return {"length": lay["length"], "spans": list(lay["spans"])}


def plan_values(plan, tables, crops, features, weights):
    L, spans = plan["length"], plan["spans"]
    years = L // 12
    warnings = weights["warnings"]
    calendar = calendar_from_spans(spans, L, crops, features, warnings)
    seasons = [{"crop_id": c, "sow_month": s % 12 + 1, "harvest_month": e % 12 + 1}
               for s, e, c in sorted(spans)]
    ctx = Ctx(seasons, calendar, crops, features, weights, {})
    pts = {"improve_soil": 0.0, "reduce_erosion": 0.0, "forage": 0.0}
    for rule in _RULES:
        for w in rule(ctx).why:
            pts[w["priority"]] += w["points"]
    deficit = sum(tables.deficit[c["crop_id"]][c["month"] - 1] for r in calendar for c in r["months"]
                  if c["crop_id"] not in (None, "fallow"))
    out = {"deficit_mm": deficit / years}
    for kind in ("bad", "avg", "good"):
        tot = 0.0
        for s, e, c in spans:
            factor = (e - s + 1) / 12 if val(crops, c, "perennial") else 1
            tot += income_per_sowing(tables, c, kind) * factor
        out["revenue_" + kind] = tot / years
    if tables.income_mode == "profit":
        out["profit_avg"] = out["revenue_avg"] - sum(
            (tables.cost[c] or 0.0) * ((e - s + 1) / 12 if val(crops, c, "perennial") else 1)
            for s, e, c in spans) / years
    else:
        out["profit_avg"] = None
    out["u"] = {"save_water": -out["deficit_mm"], "improve_soil": pts["improve_soil"],
                "extra_income": out["profit_avg"] if tables.income_mode == "profit" else out["revenue_avg"],
                "reduce_erosion": pts["reduce_erosion"], "forage": pts["forage"]}  # rule points are already per year
    return out
