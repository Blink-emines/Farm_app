"""score(features, request) -> StrategyResponse. Rule-based, no ML."""
import json
from datetime import datetime, timezone

from .loaders import (DEFAULT_SOURCE, UNKNOWN, field as crop_field, load_crops, load_weights,
                      val, validators)
from .messages import msg
from .rules import RULES, Ctx, soil_steps
from .season_calendar import build_calendar, calendar_from_spans, water_need_mm
from .action_steps import action_steps

PRIORITIES = ["save_water", "improve_soil", "extra_income", "reduce_erosion", "forage"]
LOWERING_GAPS = {"gap_kc_unknown", "gap_climate_month_missing", "gap_default_months"}


class MonthsUnknown(ValueError):
    """Sow/harvest month unknown in both the request and crops.yaml."""


def minmax(values):
    """Scale to 0-100; all equal -> 50. The one place to change how scores are normalised."""
    lo, hi = min(values), max(values)
    if hi == lo:
        return [50.0] * len(values)
    return [100.0 * (v - lo) / (hi - lo) for v in values]


def resolve_seasons(crop_ids, request_seasons, crops):
    """Months from the request win; otherwise crops.yaml defaults. Returns (seasons, crops_using_defaults)."""
    seasons, defaults = [], []
    for i, cid in enumerate(crop_ids):
        given = request_seasons[i] if request_seasons else {}
        out = {"crop_id": cid}
        for key in ("sow_month", "harvest_month"):
            if cid == "fallow" or val(crops, cid, "perennial"):
                out[key] = 1 if key == "sow_month" else 12  # placeholder: the calendar sets the real slot
                continue
            if key in given:
                out[key] = given[key]
                continue
            v = val(crops, cid, key)
            if not isinstance(v, int):
                raise MonthsUnknown(f"{key} for {cid} is not in the request and is unknown in crops.yaml")
            out[key] = v
            if crop_field(crops, cid, key)["source"] == DEFAULT_SOURCE:
                defaults.append(cid)
        seasons.append(out)
    return seasons, sorted(set(defaults))


def _dedupe(items, key):
    seen, out = set(), []
    for it in items:
        k = key(it)
        if k not in seen:
            seen.add(k)
            out.append(it)
    return out


def _calendar_messages(calendar):
    """Months per stress kind from the calendar, for the risk entries."""
    kinds = {"stress_water_deficit": set(), "stress_frost_generic": set(), "stress_heat_generic": set()}
    for row in calendar:
        for c in row["months"]:
            for r in c["stress_reasons"]:
                kinds[r["code"]].add(c["month"])
    return kinds


# No reliable yield source for these crops (olive yields are not the yield of a crop between olive trees).
NO_YIELD_SOURCE = {"olive_intercrop"}


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _facts(ctx, econ, soil):
    """Plain facts for the compare cards. return.relative_to_current is filled in by score()."""
    years = ctx.n_years or 1
    need, unknown = 0.0, False
    for _, c in ctx.months():
        if c["crop_id"] in (None, "fallow"):
            continue
        n = water_need_mm(ctx.crops, c["crop_id"], ctx.features, c["month"])
        if n is None:
            unknown = True
        else:
            need += n
    dry = sum(1 for _, c in ctx.months() if any(r["code"] == "stress_water_deficit" for r in c["stress_reasons"]))
    out = []
    for cid in dict.fromkeys(ctx.ids):
        if cid == "fallow":
            continue
        y = (econ.get("crops", {}).get(cid) or {}).get("yield_t_per_ha") or {}
        ok = cid not in NO_YIELD_SOURCE and all(_num(y.get(k)) for k in ("min", "mean", "max"))
        out.append({"crop_id": cid,
                    "yield_t_per_ha": {k: round(y[k], 2) for k in ("min", "mean", "max")} if ok else None,
                    "source": y.get("source") if ok else None})
    return {"water_need_mm_per_year": None if unknown else round(need / years),
            "dry_months_per_year": round(dry / years, 1),
            "soil_points": round(sum(s["points"] for s in soil), 2),
            "return": {"crops": out, "relative_to_current": "current"}}


def evaluate(strategy_id, is_current, crop_ids, seasons, defaults, crops, features, weights, plan=None, econ=None):
    """plan = {"length", "spans": [(start, end, crop)]} (from the optimiser) replaces the layout of `seasons`."""
    names = {s["id"]: s["name"] for s in features["sources"]}
    if plan is None:
        calendar, seasons = build_calendar(seasons, crops, features, weights["warnings"])
    else:
        calendar = calendar_from_spans(plan["spans"], plan["length"], crops, features, weights["warnings"])
        seasons = [{"crop_id": c, "sow_month": s % 12 + 1, "harvest_month": e % 12 + 1}
                   for s, e, c in sorted(plan["spans"])]
    ctx = Ctx(seasons, calendar, crops, features, weights, names)
    why, gaps, evidence = [], [], []
    for rule in RULES:
        r = rule(ctx)
        why += r.why
        gaps += r.gaps
        evidence += r.evidence
    real = sorted({c for c in crop_ids if c != "fallow"})
    gaps.append(msg("gap_local_prices"))
    gaps.append(msg("gap_water_stress_indicative"))
    unassessed = [c for c in real if crop_field(crops, c, "frost_tolerance")["value"] == UNKNOWN
                  or crop_field(crops, c, "heat_threshold_c")["value"] == UNKNOWN]
    if unassessed:
        gaps.append(msg("gap_frost_heat_tolerance_unknown", crops=",".join(unassessed)))
    if any(c["crop_id"] not in (None, "fallow") and c["month"] in (12, 1, 2)
           for _, c in ctx.months()):
        gaps.append(msg("gap_frost_underestimated"))
    if defaults:
        gaps.append(msg("gap_default_months", crops=",".join(defaults)))
    kinds = _calendar_messages(calendar)
    risks = [msg("risk_local_review")]
    ms = lambda s: ",".join(str(m) for m in sorted(s))
    if kinds["stress_water_deficit"]:
        risks.append(msg("risk_water_stress_months", months=ms(kinds["stress_water_deficit"])))
    fh = kinds["stress_frost_generic"] | kinds["stress_heat_generic"]
    if fh:
        risks.append(msg("risk_frost_heat_generic", months=ms(fh)))
        mf = features["climate"]["monthly"]
        for name, ser in (("frost_days", mf["frost_days"]), ("heat_days.35", mf["heat_days"]["35"])):
            evidence.append({"feature": f"climate.monthly.{name}", "value": ser["values"],
                             "unit": ser["unit"], "months": sorted(fh),
                             "source": names.get(ser["source"], ser["source"])})
    if unassessed:
        risks.append(msg("risk_frost_heat_unassessed"))
    raw = {p: 0.0 for p in PRIORITIES}
    for w in why:
        raw[w["priority"]] += w["points"]
    benefits = [msg("benefit_" + w["rule_id"]) for w in why if w["points"] > 0]
    if econ is None:
        from .optimize.objectives import load_economics
        econ = load_economics()
    facts = _facts(ctx, econ, soil_steps(ctx))
    gaps = _dedupe(gaps, lambda g: json.dumps(g, sort_keys=True))
    confidence = "low" if any(g["code"] in LOWERING_GAPS for g in gaps) else "medium"
    label = " > ".join(crop_ids)
    return {
        "id": strategy_id,
        "name": msg("strategy_name_current" if is_current else "strategy_name_template", crops=label),
        "is_current": is_current, "seasons": seasons, "calendar": calendar, "why": why,
        "evidence": _dedupe(evidence, lambda e: (e["feature"], tuple(e.get("months", [])))),
        "benefits": _dedupe(benefits, lambda b: b["code"]),
        "information_gaps": gaps, "risks_for_local_review": risks, "confidence": confidence,
        "facts": facts, "soil_steps": soil_steps(ctx), "action_steps": action_steps(seasons, calendar, crops),
        "_raw": raw,
    }


def _priority_weights(priorities):
    total = sum(priorities.values())
    if total == 0:
        return {p: 1 / len(PRIORITIES) for p in PRIORITIES}
    return {p: priorities[p] / total for p in PRIORITIES}


def _apply_scores(strategies, pw):
    """Fill score and rank from each strategy's _raw (min-max across `strategies`)."""
    for p in PRIORITIES:
        for s, v in zip(strategies, minmax([s["_raw"][p] for s in strategies])):
            s.setdefault("_bp", {})[p] = v
    for s in strategies:
        bp = {p: round(s["_bp"][p], 2) for p in PRIORITIES}
        s["score"] = {"total": round(sum(pw[p] * s["_bp"][p] for p in PRIORITIES), 2), "by_priority": bp}


def score(features, request, crops=None, weights=None):
    """features: valid features.json; request: valid StrategyRequest -> StrategyResponse dict."""
    from .templates import TEMPLATES
    v_feat, v_req, v_resp = validators()
    for validator, obj, what in ((v_feat, features, "features"), (v_req, request, "request")):
        errs = sorted(validator.iter_errors(obj), key=lambda e: list(e.path))
        if errs:
            raise ValueError(f"invalid {what}: {errs[0].message} at {list(errs[0].path)}")
    crops = crops or load_crops()
    weights = weights or load_weights()

    req_seasons = request["current_rotation"]["seasons"]
    cur_ids = [s["crop_id"] for s in req_seasons]
    seasons, defaults = resolve_seasons(cur_ids, req_seasons, crops)
    from .optimize.objectives import load_economics
    econ = load_economics()
    pool = [evaluate("current_rotation", True, cur_ids, seasons, defaults, crops, features, weights, econ=econ)]
    candidates = [t for t in TEMPLATES if t["crops"] != cur_ids]  # the current one is shown once
    allowed_note = None
    required = request.get("required_crop")
    if required:
        # The crop must be in every alternative: templates that contain it, plus "required then X"
        # for every other allowed crop (all crops when none are given), scored by the same rules.
        partners = [c for c in (request.get("allowed_crops") or list(crops)) if c != required]
        partners = list(dict.fromkeys(partners + ["fallow"]))
        generated = [{"id": f"with_{required}_{x}", "crops": [required, x]} for x in partners]
        seen, candidates = set(), []
        for t in [t for t in TEMPLATES if required in t["crops"]] + generated:
            key = tuple(t["crops"])
            if key not in seen and t["crops"] != cur_ids:
                seen.add(key)
                candidates.append(t)
        allowed_note = "note_required_crop"
    elif "allowed_crops" in request:
        allowed = set(request["allowed_crops"]) | {"fallow"}
        local = [t for t in candidates if set(t["crops"]) <= allowed]
        # The response needs at least 2 alternatives; with too few local ones, show them all and say so.
        if len(local) >= 2:
            allowed_note = "note_allowed_crops" if len(local) < len(candidates) else None
            candidates = local
        else:
            allowed_note = "note_allowed_crops_too_few"
    for t in candidates:
        try:
            ts, td = resolve_seasons(t["crops"], None, crops)
        except MonthsUnknown:
            continue  # a generated rotation with a crop whose months are unknown is not proposed
        pool.append(evaluate(t["id"], False, t["crops"], ts, td, crops, features, weights, econ=econ))

    pw = _priority_weights(request["priorities"])
    _apply_scores(pool, pw)  # normalised over ALL candidates
    templates = sorted(pool[1:], key=lambda s: (-s["score"]["total"], s["id"]))
    chosen = [pool[0]] + templates[: weights["templates_returned"]]
    if weights["normalise_over"] == "returned":
        for s in chosen:
            s.pop("_bp", None)
        _apply_scores(chosen, pw)
    chosen.sort(key=lambda s: (-s["score"]["total"], not s["is_current"], s["id"]))
    cur_income = pool[0]["_raw"]["extra_income"]
    for rank, s in enumerate(chosen, 1):
        s["rank"] = rank
        if not s["is_current"]:
            d = s["_raw"]["extra_income"] - cur_income  # income_flag rule points (qualitative)
            s["facts"]["return"]["relative_to_current"] = "more" if d > 0.5 else "less" if d < -0.5 else "similar"
        s.pop("_raw"), s.pop("_bp")

    notes = [msg("note_relative_scores"), msg("note_local_expert"), msg("note_normalisation")]
    notes.append(msg("note_soil_not_scored"))
    if allowed_note:
        notes.append(msg(allowed_note))
    period = features["climate"]["period"]
    response = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "location": {"latitude": request["latitude"], "longitude": request["longitude"]},
        "features_summary": {
            "climate_period": {"start_year": period["start_year"], "end_year": period["end_year"]},
            "soil_status": features["soil"]["status"],
            "data_gaps": [g["code"] for g in features["data_gaps"]],
        },
        "priorities": request["priorities"],
        "strategies": chosen,
        "notes": notes,
    }
    errs = sorted(v_resp.iter_errors(response), key=lambda e: list(e.path))
    if errs:
        raise ValueError(f"engine produced an invalid response: {errs[0].message} at {list(errs[0].path)}")
    return response
