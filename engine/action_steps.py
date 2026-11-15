"""Step-by-step action plan for one strategy, in timeline order.

Every step comes from the calendar (rows start at the first sowing) and names where it
comes from: the crop calendar (season_calendar) or a scoring rule (water_demand_match,
bare_months_penalty, family_break). No advice without one of these. Reasons are
parameter-free messages so they can be recorded as audio clips.
"""
from .loaders import families, val
from .messages import msg


def _flat(calendar):
    return [c for row in calendar for c in row["months"]]


def _spans(months):
    """Consecutive months with the same crop_id (None = bare)."""
    out = []
    for i, m in enumerate(months):
        if out and out[-1]["crop"] == m["crop_id"]:
            out[-1]["end"] = i
        else:
            out.append({"start": i, "end": i, "crop": m["crop_id"]})
    return out


def _runs(indexes):
    """Group sorted indexes into runs of consecutive values."""
    runs = []
    for i in indexes:
        if runs and i == runs[-1][-1] + 1:
            runs[-1].append(i)
        else:
            runs.append([i])
    return runs


def _step(action, months, crop_id, rule_id, message):
    return {"months": months, "action": action, "crop_id": crop_id, "rule_id": rule_id, "message": message}


def action_steps(seasons, calendar, crops):
    months = _flat(calendar)
    ids = [s["crop_id"] for s in seasons]
    spans = _spans(months)
    crop_spans = [sp for sp in spans if sp["crop"] is not None]
    by_season = len(crop_spans) == len(ids)  # spans line up with seasons (normal case)
    steps = []  # (position, order within position, step)

    for sp in spans:
        cid, a, b = sp["crop"], sp["start"], sp["end"]
        ms = [months[i]["month"] for i in range(a, b + 1)]
        if cid is None:
            steps.append((a, 0, _step("cover_bare", ms, None, "bare_months_penalty", msg("step_bare_why"))))
            continue
        if cid == "fallow":
            steps.append((a, 0, _step("cover_bare", ms, "fallow", "bare_months_penalty", msg("step_fallow_why"))))
            continue

        if by_season:
            k = crop_spans.index(sp)
            prev = ids[k - 1]  # cyclic: the rotation repeats
            fp, fc = families(crops, prev), families(crops, cid)
            if fp and fc and fp & fc and not (prev == cid and val(crops, cid, "perennial")):
                steps.append((a, 0, _step("avoid", [ms[0]], cid, "family_break", msg("step_avoid_family_why"))))

        annual = not val(crops, cid, "perennial")
        if annual:
            steps.append((a, 1, _step("sow", [ms[0]], cid, "season_calendar", msg("step_sow_why"))))
        else:  # the calendar gives a perennial a whole 12-month slot: set up once, then it stays
            steps.append((a, 1, _step("sow", [ms[0]], cid, "season_calendar", msg("step_perennial_why"))))
        dry = [i for i in range(a, b + 1)
               if any(r["code"] == "stress_water_deficit" for r in months[i]["stress_reasons"])]
        for run in _runs(dry):
            steps.append((run[0], 2, _step("watch_water", [months[i]["month"] for i in run], cid,
                                           "water_demand_match", msg("step_water_why"))))
        if annual:
            steps.append((b, 3, _step("harvest", [ms[-1]], cid, "season_calendar", msg("step_harvest_why"))))

    return [s for _, _, s in sorted(steps, key=lambda x: (x[0], x[1]))]
