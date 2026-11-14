from engine.optimize.windows import sowing_windows


def test_autumn_window_opens_when_rain_reaches_half_et0(features_mock, crops, weights):
    # mock: precip/et0 is 0.53 in October (first month >= 0.5 after the dry summer)
    win, fallback = sowing_windows(features_mock, crops, weights)
    n = weights["optimiser"]["sowing_windows"]["window_months"]
    assert win["wheat"] == [10, 11, 12] and n == 3


def test_spring_window_needs_warm_nights_and_no_frost(features_mock, crops, weights):
    # mock: March has t2m_min 7 but 1 frost day (not < 1); April is the first clean month
    win, _ = sowing_windows(features_mock, crops, weights)
    assert win["sunflower"][0] == 4 and 3 not in win["sunflower"]


def test_perennials_and_fallow_have_no_window(features_mock, crops, weights):
    win, _ = sowing_windows(features_mock, crops, weights)
    for c in ("alfalfa", "olive_intercrop", "fallow"):
        assert win[c] == list(range(1, 13))


def test_fallback_to_default_month_when_nothing_qualifies(features_mock, crops, weights):
    f = __import__("copy").deepcopy(features_mock)
    f["climate"]["monthly"]["t2m_min"]["values"] = [-5.0] * 12   # never warm enough
    win, fallback = sowing_windows(f, crops, weights)
    assert "sunflower" in fallback and win["sunflower"] == [3, 4, 5]   # default 4 +/- 1


def test_window_params_come_from_weights(features_mock, crops, weights):
    w = __import__("copy").deepcopy(weights)
    w["optimiser"]["sowing_windows"]["window_months"] = 1
    win, _ = sowing_windows(features_mock, crops, w)
    assert len(win["wheat"]) == 1
