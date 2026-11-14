"""Sowing windows derived from a point's NASA climate (features), with the approved
default months as a fallback. All levels live in weights.yaml (optimiser.sowing_windows).

Autumn crops: the window opens at the first month, scanning forward from the driest month
(lowest precipitation / ET0), where precipitation >= ratio x ET0. The ratio 0.5 is the FAO
agro-ecological zoning definition of the start of the growing period (Kassam et al.).
Spring crops: scanning forward from the coldest month (lowest t2m_min), the window opens at
the first month with t2m_min >= a generic level and frost_days below a generic level.
Both windows stay open for `window_months` months (assumption, labelled in weights.yaml).
Crops with sowing_season "any" (perennials, fallow) have no window."""
from ..loaders import val

ALL = list(range(1, 13))


def _m(features, name):
    return features["climate"]["monthly"][name]["values"]


def _scan(order, ok):
    for i in order:
        if ok(i):
            return i
    return None


def _window(first, n):
    return [((first + k) % 12) + 1 for k in range(n)]  # first is a 0-based month index


def autumn_open(features, cfg):
    p, e = _m(features, "precipitation"), _m(features, "et0")
    if any(v is None for v in p + e):
        return None
    dry = min(range(12), key=lambda i: p[i] / e[i] if e[i] else float("inf"))
    order = [(dry + k) % 12 for k in range(1, 13)]
    return _scan(order, lambda i: e[i] > 0 and p[i] >= cfg["rain_to_et0_ratio"] * e[i])


def spring_open(features, cfg):
    tmin, frost = _m(features, "t2m_min"), _m(features, "frost_days")
    if any(v is None for v in tmin + frost):
        return None
    cold = min(range(12), key=lambda i: tmin[i])
    order = [(cold + k) % 12 for k in range(1, 13)]
    return _scan(order, lambda i: tmin[i] >= cfg["spring_min_t2m_min_c"] and frost[i] < cfg["spring_max_frost_days"])


def sowing_windows(features, crops, weights):
    """Returns ({crop: [months]}, [crops that fell back to the default month +/- margin])."""
    cfg = weights["optimiser"]["sowing_windows"]
    opens = {"autumn": autumn_open(features, cfg), "spring": spring_open(features, cfg)}
    windows, fallback = {}, []
    for cid in crops:
        kind = val(crops, cid, "sowing_season")
        if kind == "any" or kind is None:
            windows[cid] = list(ALL)
            continue
        first = opens[kind]
        if first is not None:
            windows[cid] = _window(first, cfg["window_months"])
        else:
            d = val(crops, cid, "sow_month") - 1
            m = cfg["fallback_margin_months"]
            windows[cid] = sorted({((d + k) % 12) + 1 for k in range(-m, m + 1)})
            fallback.append(cid)
    return windows, fallback
