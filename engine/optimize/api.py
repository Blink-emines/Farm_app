"""optimize(features, request) -> OptimizeResponse (see engine/optimize.schema.draft.json)."""
import json
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from ..loaders import CONTRACTS, load_crops, load_weights, validators
from ..messages import msg
from ..scorer import PRIORITIES, _priority_weights, evaluate, resolve_seasons
from .model import FarmModel
from .objectives import (OBJ, build_tables, load_economics, plan_from_crops, plan_values)
from .windows import sowing_windows

DRAFT = Path(__file__).resolve().parent.parent / "optimize.schema.draft.json"
UNITS = {"save_water": "mm/year (minus the water deficit)", "improve_soil": "rule points/year",
         "extra_income": "MAD/ha/year", "reduce_erosion": "rule points/year", "forage": "rule points/year"}


def _request_validator():
    strat = json.loads((CONTRACTS / "strategy.schema.json").read_text())
    opt = json.loads(DRAFT.read_text())
    reg = Registry().with_resource(strat["$id"], Resource.from_contents(strat))
    return Draft202012Validator({"$schema": opt["$schema"], "$defs": opt["$defs"],
                                 "$ref": "#/$defs/OptimizeRequest"}, registry=reg)


def _wavg(areas, values):
    return sum(a * v for a, v in zip(areas, values)) / sum(areas)


def _strategy(sid, is_current, plan, rank, pv, farm, pw, tables, crops, features, weights, econ,
              fallback, window_crops):
    ids = [c for _, _, c in sorted(plan["spans"])]
    s = evaluate(sid, is_current, ids, [], [], crops, features, weights, plan=plan)
    s.pop("_raw")
    by = {k: round(100 * farm.norm(k, pv["u"][k]), 2) for k in OBJ}
    s["score"] = {"total": round(sum(pw[k] * by[k] for k in PRIORITIES), 2), "by_priority": by}
    s["rank"] = rank
    real = sorted({c for c in ids if c != "fallow"})
    gaps = s["information_gaps"]
    priced_gap = [c for c in real if c in tables.unpriced]
    if priced_gap:
        gaps.append(msg("gap_no_price_crops", crops=",".join(priced_gap)))
    if tables.income_mode == "gross_revenue":
        gaps.append(msg("gap_costs_unknown"))
    gaps.append(msg("gap_yield_national"))
    fb = [c for c in real if c in fallback and c in window_crops]
    if fb:
        gaps.append(msg("gap_window_fallback", crops=",".join(fb)))
    if tables.rev_avg and any(tables.rev_avg.get(c) for c in real):
        r = [round(pv[k]) for k in ("revenue_bad", "revenue_avg", "revenue_good")]
        src = econ["sources"]["yields"]["name"] + ", " + econ["sources"]["prices"]["name"]
        s["evidence"].append({"feature": "economics.revenue_range", "value": r,
                              "unit": "MAD/ha/year (bad, average, good year: min, mean, max yield 2015-2024)",
                              "source": src})
        s["risks_for_local_review"].append(msg("risk_revenue_range", bad_mad=r[0], avg_mad=r[1], good_mad=r[2]))
    return s


def optimize(features, request, crops=None, weights=None, econ=None):
    v_feat = validators()[0]
    for validator, obj, what in ((v_feat, features, "features"), (_request_validator(), request, "request")):
        errs = sorted(validator.iter_errors(obj), key=lambda e: list(e.path))
        if errs:
            raise ValueError(f"invalid {what}: {errs[0].message} at {list(errs[0].path)}")
    crops, weights, econ = crops or load_crops(), weights or load_weights(), econ or load_economics()
    opt_cfg = weights["optimiser"]
    profile = request.get("profile")
    priorities = dict(opt_cfg["profiles"][profile]) if profile else dict(request["priorities"])
    pw = _priority_weights(priorities)

    tables = build_tables(features, crops, weights, econ, request.get("price_overrides"))
    windows, fallback = sowing_windows(features, crops, weights)
    parcels = request["parcels"]
    areas = [p["area_ha"] for p in parcels]
    irrig = [bool(p.get("irrigated", False)) for p in parcels]
    water = request.get("water", {}).get("monthly_irrigation_m3")
    budget = request.get("budget_mad")
    coupled_budget = budget is not None and tables.income_mode == "profit"
    coupled = water is not None or coupled_budget

    # Parcels that share the same constraints share one plan: one representative per class
    # (rainfed / irrigated). A water cap couples the irrigated parcels, a budget couples all.
    def key(i):
        return ("own", i) if (coupled_budget or (water is not None and irrig[i])) else ("class", irrig[i])

    reps = {}
    for i in range(len(parcels)):
        reps.setdefault(key(i), []).append(i)
    rep_keys = list(reps)
    rep_of = [rep_keys.index(key(i)) for i in range(len(parcels))]
    farm = FarmModel(tables, windows, crops, weights, features,
                     [sum(areas[i] for i in reps[k]) for k in rep_keys], water_m3=water, budget=budget,
                     irrigated=[irrig[reps[k][0]] for k in rep_keys])
    farm.payoff()
    baselines = []
    for p in parcels:
        rs = p["current_rotation"]["seasons"]
        plan = plan_from_crops([s["crop_id"] for s in rs], crops, rs)
        baselines.append((plan, plan_values(plan, tables, crops, features, weights)))
        farm.extend_nadir(baselines[-1][1]["u"])
    rep_plans, _ = farm.solve_weighted(priorities)
    plans = [rep_plans[r] for r in rep_of]
    pareto = farm.pareto(request.get("pareto_points", opt_cfg["pareto_points"])) if \
        request.get("pareto_points", opt_cfg["pareto_points"]) > 0 else []
    status = farm.last_status
    # Ties in the payoff table can hide a worse value: widen the nadir so every plan shown lies inside 0-100.
    for pl in rep_plans:
        farm.extend_nadir(plan_values(pl, tables, crops, features, weights)["u"])
    for pt in pareto:
        farm.extend_nadir(pt["u"])

    results, values, insufficient = [], [], False
    for i, p in enumerate(parcels):
        pv = plan_values(plans[i], tables, crops, features, weights)
        values.append(pv)
        bplan, bv = baselines[i]
        plan_s = _strategy(f"optimised_plan_{i + 1}", False, plans[i], 1, pv, farm, pw, tables, crops,
                           features, weights, econ, fallback, set(c for _, _, c in plans[i]["spans"]))
        base_s = _strategy(f"current_rotation_{i + 1}", True, bplan, 2, bv, farm, pw, tables, crops,
                           features, weights, econ, fallback, set())
        if water is not None and irrig[i] and all(c == "fallow" for _, _, c in plans[i]["spans"]):
            plan_s["information_gaps"].append(msg("gap_irrigation_insufficient"))
            insufficient = True
        if base_s["score"]["total"] > plan_s["score"]["total"]:
            plan_s["rank"], base_s["rank"] = 2, 1
        results.append({
            "id": p["id"], "area_ha": p["area_ha"], "irrigated": irrig[i], "plan": plan_s, "baseline": base_s,
            "values": {
                "water_deficit_mm_per_year": round(pv["deficit_mm"], 2),
                "revenue_mad_per_ha_year": round(pv["revenue_avg"], 2),
                "revenue_range_mad_per_ha_year": {"bad_year": round(pv["revenue_bad"], 2),
                                                  "average_year": round(pv["revenue_avg"], 2),
                                                  "good_year": round(pv["revenue_good"], 2)},
                "profit_mad_per_ha_year": None if pv["profit_avg"] is None else round(pv["profit_avg"], 2),
                "baseline_revenue_mad_per_ha_year": round(bv["revenue_avg"], 2),
                "baseline_water_deficit_mm_per_year": round(bv["deficit_mm"], 2)}})

    def farm_u(k):
        return _wavg(areas, [v["u"][k] for v in values])

    objectives = {k: {"unit": UNITS[k], "ideal": round(farm.ideal[k], 3), "nadir": round(farm.nadir[k], 3),
                      "plan_value": round(farm_u(k), 3)} for k in OBJ}
    tot = sum(areas)
    rng = {n: round(sum(a * v["revenue_" + n] for a, v in zip(areas, values)), 2)
           for n in ("bad", "avg", "good")}
    totals = {"area_ha": tot,
              "gross_revenue_mad_per_year": rng["avg"],
              "revenue_range_mad_per_year": {"bad_year": rng["bad"], "average_year": rng["avg"], "good_year": rng["good"]},
              "profit_mad_per_year": None if tables.income_mode == "gross_revenue" else round(
                  sum(a * v["profit_avg"] for a, v in zip(areas, values)), 2),
              "irrigation_need_m3_per_year": round(
                  sum(a * 10 * v["deficit_mm"] for a, v, ir in zip(areas, values, irrig) if ir), 2),
              "baseline_gross_revenue_mad_per_year": round(
                  sum(a * b[1]["revenue_avg"] for a, b in zip(areas, baselines)), 2)}

    par_out = []
    for pt in sorted(pareto, key=lambda q: q["u"]["extra_income"]):
        pplans = [pt["plans"][r] for r in rep_of]
        pvs = [plan_values(pl, tables, crops, features, weights) for pl in pplans]
        par_out.append({
            "revenue_mad_per_ha_year": round(_wavg(areas, [v["revenue_avg"] for v in pvs]), 2),
            "water_deficit_mm_per_year": round(_wavg(areas, [v["deficit_mm"] for v in pvs]), 2),
            "profit_mad_per_ha_year": None if tables.income_mode == "gross_revenue" else round(
                _wavg(areas, [v["profit_avg"] for v in pvs]), 2),
            "scores": {"extra_income": round(100 * farm.norm("extra_income", pt["u"]["extra_income"]), 2),
                       "save_water": round(100 * farm.norm("save_water", pt["u"]["save_water"]), 2)},
            "crops": [" > ".join(c for _, _, c in sorted(pl["spans"])) for pl in pplans]})

    gaps = []
    if insufficient:
        gaps.append(msg("gap_irrigation_insufficient"))
    if fallback:
        gaps.append(msg("gap_window_fallback", crops=",".join(sorted(fallback))))
    notes = [msg("note_relative_scores"), msg("note_local_expert"), msg("note_optimiser"),
             msg("note_normalisation"), msg("note_soil_not_scored")]
    response = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "location": {"latitude": request["latitude"], "longitude": request["longitude"]},
        "profile": profile, "priorities": priorities,
        "solver": {"status": status, "time_s": round(farm.time_used, 3),
                   "backend": "HiGHS via Pyomo (appsi_highs)", "solves": 0, "coupled": coupled},
        "objectives": objectives, "windows": {c: windows[c] for c in windows},
        "parcels": results, "totals": totals, "pareto": par_out, "information_gaps": gaps, "notes": notes}
    response["solver"]["solves"] = farm.n_solves
    return response
