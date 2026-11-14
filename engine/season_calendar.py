"""12-month calendar per rotation year: growing / stress / bare."""
from .loaders import val
from .messages import msg


def _after(t, month):
    """Smallest absolute month index > t that falls on calendar `month` (1-12)."""
    a = t + 1
    return a + ((month - 1 - a) % 12)


def layout(seasons, crops):
    """Cyclic timeline of the rotation (absolute month index 0 = January of row 1).

    Each annual season is sown at the first occurrence of its sow month AFTER the previous
    harvest and harvested at the first occurrence of its harvest month after sowing.
    Fallow and perennials take a 12-month slot starting the month after the previous harvest.
    The cycle repeats; its length is rounded up to whole years.
    Returns {spans: [(start, end, crop)], slots, length, t0, seasons}."""
    spans, out, prev_end = [], [], None
    for s in seasons:
        cid = s["crop_id"]
        whole_slot = cid == "fallow" or val(crops, cid, "perennial")
        if whole_slot:
            start = 0 if prev_end is None else prev_end + 1
            end = start + 11
            out.append({"crop_id": cid, "sow_month": start % 12 + 1, "harvest_month": end % 12 + 1})
        else:
            start = s["sow_month"] - 1 if prev_end is None else _after(prev_end, s["sow_month"])
            end = start + (s["harvest_month"] - s["sow_month"]) % 12
            out.append(dict(s))
        spans.append((start, end, cid))
        prev_end = end
    first = seasons[0]
    first_whole = spans[0][2] == "fallow" or val(crops, first["crop_id"], "perennial")
    next_start = prev_end + 1 if first_whole else _after(prev_end, first["sow_month"])
    t0 = spans[0][0]
    length = -(-(next_start - t0) // 12) * 12
    slots = [None] * length
    for start, end, cid in spans:
        for a in range(start, end + 1):
            slots[(a - t0) % length] = cid
    return {"spans": spans, "slots": slots, "length": length, "t0": t0, "seasons": out}


def _monthly(features, name, m):
    return features["climate"]["monthly"][name]["values"][m - 1]


def water_need_mm(crops, crop, features, m):
    """Kc_mid x et0, or None if Kc or et0 is unknown (rule water_demand_match)."""
    kc, et0 = val(crops, crop, "kc_mid"), _monthly(features, "et0", m)
    if not isinstance(kc, (int, float)) or et0 is None:
        return None
    return kc * et0


def month_stress(crops, crop, features, m, warnings):
    """Reasons a growing month is stressed (water deficit, generic frost, generic heat)."""
    reasons = []
    need, rain = water_need_mm(crops, crop, features, m), _monthly(features, "precipitation", m)
    if need is not None and rain is not None and need > rain:
        reasons.append(msg("stress_water_deficit", crop=crop, need_mm=round(need), rain_mm=round(rain)))
    frost = _monthly(features, "frost_days", m)
    if frost is not None and frost >= warnings["frost_days_min"]:
        reasons.append(msg("stress_frost_generic", crop=crop, frost_days=round(frost, 1),
                           level=warnings["frost_days_min"]))
    thr = str(warnings["heat_threshold_c"])
    heat = features["climate"]["monthly"]["heat_days"][thr]["values"][m - 1]
    if heat is not None and heat >= warnings["heat_days_min"]:
        reasons.append(msg("stress_heat_generic", crop=crop, heat_days=round(heat, 1),
                           threshold_c=warnings["heat_threshold_c"], level=warnings["heat_days_min"]))
    return reasons


def build_calendar(seasons, crops, features, warnings):
    """Returns (calendar rows, seasons with the months actually used)."""
    lay = layout(seasons, crops)
    rows = []
    for y in range(lay["length"] // 12):
        months = []
        for m in range(1, 13):
            crop = lay["slots"][(12 * y + m - 1 - lay["t0"]) % lay["length"]]
            if crop is None:
                months.append({"month": m, "crop_id": None, "status": "bare", "stress_reasons": []})
            elif crop == "fallow":
                months.append({"month": m, "crop_id": "fallow", "status": "bare", "stress_reasons": []})
            else:
                reasons = month_stress(crops, crop, features, m, warnings)
                months.append({"month": m, "crop_id": crop,
                               "status": "stress" if reasons else "growing", "stress_reasons": reasons})
        rows.append({"year": y + 1, "months": months})
    return rows, lay["seasons"]
