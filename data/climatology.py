"""Daily NASA POWER values -> 12-month climatology (average over the complete years in the data)."""
import numpy as np
import pandas as pd

from .et0 import et0_from_daily

HEAT_THRESHOLDS = (30, 32, 35, 38)


def _to_list(per_month, digits):
    """Series indexed 1..12 -> list of 12 floats, NaN -> None."""
    per_month = per_month.reindex(range(1, 13))
    return [None if pd.isna(v) else round(float(v), digits) for v in per_month]


def _ym(s):
    return [s.index.year, s.index.month]


def _total_ym(s):
    g = s.groupby(_ym(s))
    return g.sum(min_count=1).where(g.count() == g.size())


def _total_year(s):
    g = s.groupby(s.index.year)
    return g.sum(min_count=1).where(g.count() == g.size())


def _flag(condition, source):
    return condition.astype(float).where(source.notna())


def _with_et0(df, latitude, elevation):
    df = df.copy()
    # ET0 needs an elevation for pressure; NASA gives one, otherwise assume the pilot-area mean.
    df["et0"] = et0_from_daily(df, latitude, elevation if elevation is not None else 575.0)
    return df


def yearly_series(df, latitude, elevation):
    """Year-by-year values from the same daily data. Years with a gap in the needed variable are None."""
    df = _with_et0(df, latitude, elevation)
    years = sorted(int(y) for y in df.index.year.unique())

    def per_year(series):
        series = series.reindex(years)
        return [None if pd.isna(v) else round(float(v), 2) for v in series]

    precip, et0 = _total_year(df["PRECTOTCORR"]), _total_year(df["et0"])
    monthly = _total_ym(df["PRECTOTCORR"])
    return {
        "years": years,
        "precipitation": per_year(precip),
        "et0": per_year(et0),
        "water_balance": per_year(precip - et0),
        "frost_days": per_year(_total_year(_flag(df["T2M_MIN"] < 0, df["T2M_MIN"]))),
        "heat_days_35": per_year(_total_year(_flag(df["T2M_MAX"] > 35, df["T2M_MAX"]))),
        "precipitation_monthly": [
            _to_list(monthly.xs(y, level=0) if y in monthly.index.get_level_values(0) else pd.Series(dtype=float), 2)
            for y in years
        ],
    }


def monthly_climatology(df, latitude, elevation):
    """Return {feature: 12 values (or {threshold: 12 values} for heat_days)}.

    Sums and day counts only use months where every day has data; means use the valid days.
    A calendar month with no valid year is None (never 0)."""
    df = _with_et0(df, latitude, elevation)
    keys = _ym(df)

    def mean_ym(s):
        return s.groupby(keys).mean()

    total_ym, flag = _total_ym, _flag

    def over_years(per_ym, digits=2):
        return _to_list(per_ym.groupby(level=1).mean(), digits)

    precip, et0 = total_ym(df["PRECTOTCORR"]), total_ym(df["et0"])
    heat = {
        str(t): over_years(total_ym(flag(df["T2M_MAX"] > t, df["T2M_MAX"])))
        for t in HEAT_THRESHOLDS
    }
    return {
        "t2m_mean": over_years(mean_ym(df["T2M"])),
        "t2m_max": over_years(mean_ym(df["T2M_MAX"])),
        "t2m_min": over_years(mean_ym(df["T2M_MIN"])),
        "precipitation": over_years(precip),
        "et0": over_years(et0),
        "water_balance": over_years(precip - et0),
        "rh2m": over_years(mean_ym(df["RH2M"])),
        "ws2m": over_years(mean_ym(df["WS2M"])),
        "solar_radiation": over_years(mean_ym(df["ALLSKY_SFC_SW_DWN"])),
        "root_zone_wetness": over_years(mean_ym(df["GWETROOT"]), 3),
        "frost_days": over_years(total_ym(flag(df["T2M_MIN"] < 0, df["T2M_MIN"]))),
        "heat_days": heat,
    }
