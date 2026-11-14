import math

import numpy as np
import pandas as pd
import pytest

from data import climatology


def make_df(years=(2023, 2024), **overrides):
    idx = pd.date_range(f"{years[0]}-01-01", f"{years[-1]}-12-31", freq="D")
    base = {"T2M": 15.0, "T2M_MAX": 22.0, "T2M_MIN": 8.0, "PRECTOTCORR": 1.0,
            "RH2M": 60.0, "WS2M": 2.0, "ALLSKY_SFC_SW_DWN": 15.0, "GWETROOT": 0.5}
    df = pd.DataFrame({k: float(v) for k, v in base.items()}, index=idx)
    for k, v in overrides.items():
        df[k] = v
    return df


def test_precipitation_is_monthly_sum_averaged_over_years():
    m = climatology.monthly_climatology(make_df(), latitude=33.96, elevation=575.0)
    assert m["precipitation"][0] == pytest.approx(31.0)   # January: 31 days x 1 mm
    assert m["precipitation"][1] == pytest.approx((28 + 29) / 2)  # Feb: 2023 and leap 2024


def test_frost_and_heat_days_are_counted_from_daily_values():
    df = make_df()
    for year in (2023, 2024):
        jan = df.index[(df.index.year == year) & (df.index.month == 1)]
        df.loc[jan[:5], "T2M_MIN"] = -2.0          # 5 frost days every January
        jul = df.index[(df.index.year == year) & (df.index.month == 7)]
        df.loc[jul[:3], "T2M_MAX"] = 36.0          # 3 days above 35 but not above 38
        df.loc[jul[3], "T2M_MAX"] = 30.0           # exactly 30 is NOT above 30
    m = climatology.monthly_climatology(df, 33.96, 575.0)
    assert m["frost_days"][0] == pytest.approx(5.0)
    assert m["frost_days"][6] == pytest.approx(0.0)
    assert m["heat_days"]["30"][6] == pytest.approx(3.0)
    assert m["heat_days"]["35"][6] == pytest.approx(3.0)
    assert m["heat_days"]["38"][6] == pytest.approx(0.0)


def test_water_balance_is_precipitation_minus_et0():
    m = climatology.monthly_climatology(make_df(), 33.96, 575.0)
    for i in range(12):
        assert m["water_balance"][i] == pytest.approx(m["precipitation"][i] - m["et0"][i], abs=0.02)


def test_month_without_valid_data_is_null_not_zero():
    df = make_df()
    df.loc[df.index.month == 3, "PRECTOTCORR"] = np.nan
    m = climatology.monthly_climatology(df, 33.96, 575.0)
    assert m["precipitation"][2] is None
    assert m["water_balance"][2] is None
    assert m["precipitation"][0] is not None


def test_partial_month_in_one_year_is_skipped_for_sums():
    df = make_df()
    df.loc["2023-05-10", "PRECTOTCORR"] = np.nan  # May 2023 incomplete; May 2024 complete
    m = climatology.monthly_climatology(df, 33.96, 575.0)
    assert m["precipitation"][4] == pytest.approx(31.0)  # only 2024 counts


def test_no_nan_leaks_into_output():
    m = climatology.monthly_climatology(make_df(), 33.96, 575.0)
    vals = list(m["t2m_mean"]) + list(m["et0"]) + list(m["heat_days"]["32"])
    assert not any(isinstance(v, float) and math.isnan(v) for v in vals)
    assert all(len(v) == 12 for k, v in m.items() if k != "heat_days")


def test_yearly_series_aligned_and_summed():
    y = climatology.yearly_series(make_df(), 33.96, 575.0)
    assert y["years"] == [2023, 2024]
    for key in ("precipitation", "et0", "water_balance", "frost_days", "heat_days_35"):
        assert len(y[key]) == 2
    assert y["precipitation"] == [pytest.approx(365.0), pytest.approx(366.0)]
    assert y["water_balance"][0] == pytest.approx(y["precipitation"][0] - y["et0"][0], abs=0.02)
    assert len(y["precipitation_monthly"]) == 2 and all(len(m) == 12 for m in y["precipitation_monthly"])
    assert y["precipitation_monthly"][1][1] == pytest.approx(29.0)  # leap-year February
    assert sum(y["precipitation_monthly"][0]) == pytest.approx(y["precipitation"][0], abs=0.1)


def test_yearly_counts_and_missing_year_is_null():
    df = make_df()
    df.loc["2023-01-05":"2023-01-07", "T2M_MIN"] = -1.0
    df.loc["2024-07-01":"2024-07-02", "T2M_MAX"] = 40.0
    df.loc["2024-03-03", "PRECTOTCORR"] = np.nan
    y = climatology.yearly_series(df, 33.96, 575.0)
    assert y["frost_days"] == [3.0, 0.0]
    assert y["heat_days_35"] == [0.0, 2.0]
    assert y["precipitation"][1] is None and y["water_balance"][1] is None
    assert y["precipitation_monthly"][1][2] is None
