import math
from urllib.parse import parse_qs, urlparse

import pytest

from data import nasa_power, soilgrids
from data.errors import UpstreamUnavailable


def test_daily_url_has_verified_parameters_and_ag_community():
    url = nasa_power.build_url(33.96, -5.27)
    q = parse_qs(urlparse(url).query)
    assert q["community"] == ["AG"]
    assert q["start"] == ["20050101"] and q["end"] == ["20241231"]
    assert q["parameters"][0].split(",") == list(nasa_power.PARAMETERS)
    assert set(nasa_power.PARAMETERS) == {
        "T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "RH2M", "WS2M", "ALLSKY_SFC_SW_DWN", "GWETROOT"}


@pytest.mark.parametrize("point,merra,radiation", [
    ((33.96, -5.27), (34.0, -5.0), (33.5, -5.5)),
    ((33.24, -5.27), (33.0, -5.0), (33.5, -5.5)),    # just south of the 33.25 edge
    ((33.25, -5.27), (33.5, -5.0), (33.5, -5.5)),    # on the edge: northern cell
    ((33.75, -5.27), (34.0, -5.0), (33.5, -5.5)),
    ((34.00, -5.27), (34.0, -5.0), (34.5, -5.5)),    # radiation cell edge at whole degrees
    ((33.96, -5.30), (34.0, -5.0), (33.5, -5.5)),
    ((33.96, -5.35), (34.0, -5.625), (33.5, -5.5)),  # west of the -5.3125 edge
    ((33.96, -5.00), (34.0, -5.0), (33.5, -4.5)),    # radiation edge at -5.00: eastern cell
    ((20.70, -17.20), (20.5, -17.5), (20.5, -17.5)),
])
def test_cell_centres_match_probed_grid(point, merra, radiation):
    assert nasa_power.merra_cell_centre(*point) == merra
    assert nasa_power.radiation_cell_centre(*point) == radiation


def test_every_point_in_a_cell_makes_the_same_requests():
    a = nasa_power.cell_requests(33.96, -5.27)
    b = nasa_power.cell_requests(33.80, -5.10)
    assert a == b
    assert [r[2] for r in a] == [nasa_power.MERRA_PARAMETERS, nasa_power.RADIATION_PARAMETERS]


def test_cell_requests_are_made_at_the_centre_with_three_decimals():
    url = nasa_power.build_url(34.0, -5.625, nasa_power.MERRA_PARAMETERS)
    q = parse_qs(urlparse(url).query)
    assert q["latitude"] == ["34.000"] and q["longitude"] == ["-5.625"]
    assert "ALLSKY_SFC_SW_DWN" not in q["parameters"][0]


def test_parse_daily_dataframe_and_elevation(power_raw):
    df, elev = nasa_power.parse_daily(power_raw)
    assert elev == pytest.approx(575.32)
    assert df.index[0].year == 2023 and df.index[-1].year == 2024
    assert len(df) == 731
    assert list(df.columns) == list(nasa_power.PARAMETERS)


def test_fill_value_becomes_nan_never_a_number(power_raw):
    power_raw["properties"]["parameter"]["PRECTOTCORR"]["20230102"] = -999.0
    df, _ = nasa_power.parse_daily(power_raw)
    assert math.isnan(df.loc["2023-01-02", "PRECTOTCORR"])
    assert (df.fillna(0) > -990).all().all()


def test_unexpected_unit_is_rejected(power_raw):
    power_raw["parameters"]["ALLSKY_SFC_SW_DWN"]["units"] = "kW-hr/m^2/day"
    with pytest.raises(UpstreamUnavailable):
        nasa_power.parse_daily(power_raw)


def test_missing_elevation_is_none(power_raw):
    power_raw["geometry"]["coordinates"] = [-5.27, 33.96]
    _, elev = nasa_power.parse_daily(power_raw)
    assert elev is None


def test_soil_url_asks_for_five_properties_three_depths():
    q = parse_qs(urlparse(soilgrids.build_url(33.96, -5.27)).query)
    assert sorted(q["property"]) == ["clay", "phh2o", "sand", "silt", "soc"]
    assert q["depth"] == ["0-5cm", "5-15cm", "15-30cm"]
    assert q["value"] == ["mean"] and q["lat"] == ["33.96"] and q["lon"] == ["-5.27"]


def test_soil_conversion_uses_d_factor(soil_raw):
    layers = soilgrids.parse_layers(soil_raw)
    assert [l["depth"] for l in layers] == ["0-5cm", "5-15cm", "15-30cm"]
    top = layers[0]
    # raw mean values (g/kg, dg/kg, pH*10) divided by d_factor 10
    raw = {l["name"]: l["depths"][0]["values"]["mean"] for l in soil_raw["properties"]["layers"]}
    assert top["clay_pct"] == pytest.approx(raw["clay"] / 10)
    assert top["sand_pct"] == pytest.approx(raw["sand"] / 10)
    assert top["silt_pct"] == pytest.approx(raw["silt"] / 10)
    assert top["soc_g_kg"] == pytest.approx(raw["soc"] / 10)
    assert top["ph_h2o"] == pytest.approx(raw["phh2o"] / 10)
    assert 5 < top["ph_h2o"] < 10


def test_soil_null_stays_null(soil_raw):
    soil_raw["properties"]["layers"][0]["depths"][0]["values"]["mean"] = None
    layers = soilgrids.parse_layers(soil_raw)
    name = soil_raw["properties"]["layers"][0]["name"]
    key = {"clay": "clay_pct", "sand": "sand_pct", "silt": "silt_pct", "soc": "soc_g_kg", "phh2o": "ph_h2o"}[name]
    assert layers[0][key] is None


def test_soil_wrong_target_unit_is_rejected(soil_raw):
    soil_raw["properties"]["layers"][0]["unit_measure"]["target_units"] = "mg/kg"
    with pytest.raises(soilgrids.SoilParseError):
        soilgrids.parse_layers(soil_raw)
