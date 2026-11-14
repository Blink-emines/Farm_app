"""Reference evapotranspiration, FAO-56 Penman-Monteith (Allen et al. 1998, eq. 6).

Equation numbers below refer to FAO Irrigation and Drainage Paper 56. All functions
work on floats or pandas Series (vectorised)."""
import numpy as np
import pandas as pd

GSC = 0.0820          # solar constant, MJ m-2 min-1
SIGMA = 4.903e-9      # Stefan-Boltzmann, MJ K-4 m-2 day-1
ALBEDO = 0.23         # grass reference surface


def sat_vapour_pressure(t):
    """e0(T), kPa (eq. 11)."""
    return 0.6108 * np.exp(17.27 * t / (t + 237.3))


def actual_vapour_pressure(rh_mean, tmax, tmin):
    """ea from mean relative humidity (eq. 19): RHmean/100 * es, es = (e0(Tmax)+e0(Tmin))/2 (eq. 12)."""
    es = (sat_vapour_pressure(tmax) + sat_vapour_pressure(tmin)) / 2
    return rh_mean / 100.0 * es


def extraterrestrial_radiation(latitude, doy):
    """Ra, MJ m-2 day-1 (eq. 21-25)."""
    phi = np.radians(latitude)
    dr = 1 + 0.033 * np.cos(2 * np.pi * doy / 365)
    delta = 0.409 * np.sin(2 * np.pi * doy / 365 - 1.39)
    ws = np.arccos(np.clip(-np.tan(phi) * np.tan(delta), -1, 1))
    return (24 * 60 / np.pi) * GSC * dr * (
        ws * np.sin(phi) * np.sin(delta) + np.cos(phi) * np.cos(delta) * np.sin(ws))


def et0_fao56(tmean, tmax, tmin, ea, u2, rs, latitude, elevation, doy):
    """Daily ET0 in mm/day.

    tmean/tmax/tmin degC, ea kPa, u2 wind at 2 m in m/s (used as given), rs MJ m-2 day-1.
    Soil heat flux G is 0 for a daily step."""
    pressure = 101.3 * ((293 - 0.0065 * elevation) / 293) ** 5.26      # eq. 7
    gamma = 0.000665 * pressure                                         # eq. 8
    delta = 4098 * sat_vapour_pressure(tmean) / (tmean + 237.3) ** 2    # eq. 13
    es = (sat_vapour_pressure(tmax) + sat_vapour_pressure(tmin)) / 2    # eq. 12

    ra = extraterrestrial_radiation(latitude, doy)
    rso = (0.75 + 2e-5 * elevation) * ra                                # eq. 37
    rns = (1 - ALBEDO) * rs                                             # eq. 38
    rel = np.clip(rs / rso, 0.0, 1.0)
    tk4 = ((tmax + 273.16) ** 4 + (tmin + 273.16) ** 4) / 2
    rnl = SIGMA * tk4 * (0.34 - 0.14 * np.sqrt(ea)) * (1.35 * rel - 0.35)  # eq. 39
    rn = rns - rnl                                                      # eq. 40

    num = 0.408 * delta * rn + gamma * 900 / (tmean + 273) * u2 * (es - ea)
    den = delta + gamma * (1 + 0.34 * u2)
    return np.maximum(num / den, 0.0)


def et0_from_daily(df, latitude, elevation):
    """ET0 (mm/day) for a DataFrame of NASA POWER daily columns.

    Needs T2M, T2M_MAX, T2M_MIN, RH2M, WS2M (already at 2 m: no height conversion), ALLSKY_SFC_SW_DWN.
    Days with any missing input give NaN."""
    ea = actual_vapour_pressure(df["RH2M"], df["T2M_MAX"], df["T2M_MIN"])
    doy = df.index.day_of_year.to_numpy()
    out = et0_fao56(df["T2M"], df["T2M_MAX"], df["T2M_MIN"], ea, df["WS2M"],
                    df["ALLSKY_SFC_SW_DWN"], latitude, elevation, doy)
    return pd.Series(out, index=df.index, name="et0")
