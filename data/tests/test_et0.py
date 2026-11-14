import math

import pandas as pd
import pytest

from data import et0


def test_fao56_example_18_uccle():
    # FAO-56 Example 18: Uccle (50.80 N, 100 m), 6 July. Published ET0 = 3.9 mm/day.
    result = et0.et0_fao56(
        tmean=16.9, tmax=21.5, tmin=12.3, ea=1.409, u2=2.078, rs=22.07,
        latitude=50.80, elevation=100.0, doy=187,
    )
    assert result == pytest.approx(3.88, abs=0.05)


def test_wind_is_used_as_given_no_height_conversion():
    # WS2M is already wind at 2 m: the 10 m -> 2 m factor (0.748) must NOT be applied.
    df = pd.DataFrame(
        {"T2M": [16.9], "T2M_MAX": [21.5], "T2M_MIN": [12.3], "RH2M": [70.0],
         "WS2M": [2.078], "ALLSKY_SFC_SW_DWN": [22.07]},
        index=pd.to_datetime(["2024-07-05"]),
    )
    got = et0.et0_from_daily(df, latitude=50.80, elevation=100.0).iloc[0]
    es = (et0.sat_vapour_pressure(21.5) + et0.sat_vapour_pressure(12.3)) / 2
    direct = et0.et0_fao56(16.9, 21.5, 12.3, ea=0.70 * es, u2=2.078, rs=22.07,
                           latitude=50.80, elevation=100.0, doy=187)
    converted = et0.et0_fao56(16.9, 21.5, 12.3, ea=0.70 * es, u2=2.078 * 0.748, rs=22.07,
                              latitude=50.80, elevation=100.0, doy=187)
    assert got == pytest.approx(direct)
    assert abs(got - converted) > 0.05


def test_actual_vapour_pressure_uses_mean_rh_and_mean_of_es_tmax_tmin():
    es = (et0.sat_vapour_pressure(30.0) + et0.sat_vapour_pressure(10.0)) / 2
    assert et0.actual_vapour_pressure(rh_mean=50.0, tmax=30.0, tmin=10.0) == pytest.approx(0.5 * es)
    # es at Tmean would be different (curve is convex), so the choice matters
    assert es > et0.sat_vapour_pressure(20.0)


def test_saturation_vapour_pressure_known_value():
    assert et0.sat_vapour_pressure(20.0) == pytest.approx(2.338, abs=0.002)


def test_missing_input_gives_nan_and_never_negative():
    df = pd.DataFrame(
        {"T2M": [10.0, math.nan], "T2M_MAX": [12.0, 20.0], "T2M_MIN": [-5.0, 10.0],
         "RH2M": [99.0, 50.0], "WS2M": [0.1, 2.0], "ALLSKY_SFC_SW_DWN": [1.0, 15.0]},
        index=pd.to_datetime(["2024-01-01", "2024-01-02"]),
    )
    out = et0.et0_from_daily(df, latitude=33.96, elevation=575.0)
    assert out.iloc[0] >= 0
    assert math.isnan(out.iloc[1])
