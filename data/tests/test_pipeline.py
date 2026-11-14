import json
from pathlib import Path

import jsonschema
import pytest

from data import cache, nasa_power, pipeline, soilgrids
from data.errors import OutsidePilotRegion, UpstreamUnavailable

SCHEMA = json.loads((Path(__file__).parents[2] / "docs/contracts/features.schema.json").read_text())


@pytest.fixture(autouse=True)
def short_period(monkeypatch):
    monkeypatch.setattr(nasa_power, "START_YEAR", 2023)
    monkeypatch.setattr(nasa_power, "END_YEAR", 2024)


def install_fetcher(monkeypatch, power_raw, soil_raw, soil_fails=False, power_fails=False):
    calls = {"power": 0, "soil": 0}

    def fake(url, **kwargs):
        if "power.larc.nasa.gov" in url:
            calls["power"] += 1
            if power_fails:
                raise UpstreamUnavailable("NASA down")
            return power_raw
        calls["soil"] += 1
        if soil_fails:
            raise UpstreamUnavailable("ISRIC down")
        return soil_raw

    monkeypatch.setattr("data.http.fetch_json", fake)
    return calls


def codes(f):
    return {g["code"] for g in f["data_gaps"]}


def test_valid_against_schema_and_period(monkeypatch, power_raw, soil_raw):
    install_fetcher(monkeypatch, power_raw, soil_raw)
    f = pipeline.get_features(33.96, -5.27)
    jsonschema.validate(f, SCHEMA)
    assert f["location"] == {"latitude": 33.96, "longitude": -5.27, "elevation_m": 575.32, "region": "saiss"}
    assert f["climate"]["period"] == {"start_year": 2023, "end_year": 2024}
    assert f["soil"]["status"] == "live" and f["soil"]["source"] == "soilgrids"
    assert {"climate_coarse_grid", "root_zone_wetness_model", "soil_model_estimate"} <= codes(f)
    assert {s["id"] for s in f["sources"]} == {"nasa_power", "soilgrids"}


def test_coordinates_are_rounded(monkeypatch, power_raw, soil_raw):
    calls = install_fetcher(monkeypatch, power_raw, soil_raw)
    f = pipeline.get_features(33.9649, -5.2701)
    assert (f["location"]["latitude"], f["location"]["longitude"]) == (33.96, -5.27)
    assert calls["power"] == 1


def test_second_call_uses_cache_and_never_repeats_requests(monkeypatch, power_raw, soil_raw):
    calls = install_fetcher(monkeypatch, power_raw, soil_raw)
    pipeline.get_features(33.96, -5.27)
    f2 = pipeline.get_features(33.96, -5.27)
    assert calls == {"power": 1, "soil": 1}
    assert f2["soil"]["status"] == "cache"
    assert all(s["cache_status"] == "cache" for s in f2["sources"])
    jsonschema.validate(f2, SCHEMA)


def test_soil_down_uses_fallback_with_gap(monkeypatch, power_raw, soil_raw):
    install_fetcher(monkeypatch, power_raw, soil_raw, soil_fails=True)
    f = pipeline.get_features(33.96, -5.27)
    jsonschema.validate(f, SCHEMA)
    assert f["soil"]["status"] == "fallback"
    assert "soil_fallback_used" in codes(f)
    src = next(s for s in f["sources"] if s["id"] == "soilgrids")
    assert src["cache_status"] == "fallback"
    assert len(f["soil"]["layers"]) == 3


def test_soil_down_and_no_fallback_is_unavailable_not_an_error(monkeypatch, power_raw, soil_raw, tmp_path):
    install_fetcher(monkeypatch, power_raw, soil_raw, soil_fails=True)
    monkeypatch.setattr(soilgrids, "FALLBACK_PATH", tmp_path / "missing.json")
    f = pipeline.get_features(33.96, -5.27)
    jsonschema.validate(f, SCHEMA)
    assert f["soil"] == {"status": "unavailable", "source": None, "layers": []}
    assert "soil_unavailable" in codes(f)
    assert {s["id"] for s in f["sources"]} == {"nasa_power"}


def test_nasa_down_and_no_cache_raises(monkeypatch, power_raw, soil_raw):
    install_fetcher(monkeypatch, power_raw, soil_raw, power_fails=True)
    with pytest.raises(UpstreamUnavailable):
        pipeline.get_features(33.96, -5.27)


def test_outside_region_raises_before_any_request(monkeypatch, power_raw, soil_raw):
    calls = install_fetcher(monkeypatch, power_raw, soil_raw)
    with pytest.raises(OutsidePilotRegion):
        pipeline.get_features(48.85, 2.35)
    assert calls == {"power": 0, "soil": 0}


def test_missing_daily_values_are_reported_as_gap(monkeypatch, power_raw, soil_raw):
    for d in list(power_raw["properties"]["parameter"]["GWETROOT"]):
        if d.startswith("2023-03") or d.startswith("202303") or d.startswith("202403"):
            power_raw["properties"]["parameter"]["GWETROOT"][d] = -999.0
    install_fetcher(monkeypatch, power_raw, soil_raw)
    f = pipeline.get_features(33.96, -5.27)
    jsonschema.validate(f, SCHEMA)
    assert f["climate"]["monthly"]["root_zone_wetness"]["values"][2] is None
    gap = next(g for g in f["data_gaps"] if g["code"] == "climate_missing_values")
    assert "climate.monthly.root_zone_wetness" in gap["affects"]


def test_no_sentinel_values_anywhere(monkeypatch, power_raw, soil_raw):
    install_fetcher(monkeypatch, power_raw, soil_raw)
    assert "-999" not in json.dumps(pipeline.get_features(33.96, -5.27))


def test_committed_sample_validates_and_matches_default_point():
    sample = json.loads((Path(__file__).parents[1] / "samples/features_default.json").read_text())
    jsonschema.validate(sample, SCHEMA)
    assert (sample["location"]["latitude"], sample["location"]["longitude"]) == (33.96, -5.27)
    assert sample["climate"]["period"] == {"start_year": 2005, "end_year": 2024}
    assert sample["soil"]["layers"]


def test_committed_fallback_is_a_saved_real_response():
    saved = json.loads((Path(__file__).parents[1] / "fallback/saiss_soil.json").read_text())
    assert saved["fetched_at"] and saved["response"]["type"] == "Feature"
    assert "rest.isric.org" in saved["endpoint"]


def test_yearly_block_aligned_with_years(monkeypatch, power_raw, soil_raw):
    install_fetcher(monkeypatch, power_raw, soil_raw)
    f = pipeline.get_features(33.96, -5.27)
    y = f["yearly"]
    assert y["years"] == [2023, 2024]
    for key in ("precipitation", "et0", "water_balance", "frost_days", "heat_days_35"):
        assert len(y[key]) == 2
    assert all(len(m) == 12 for m in y["precipitation_monthly"]) and len(y["precipitation_monthly"]) == 2
    assert y["source"] == "nasa_power"


def test_vegetation_not_downloaded_is_unavailable_with_gap(monkeypatch, power_raw, soil_raw):
    install_fetcher(monkeypatch, power_raw, soil_raw)
    f = pipeline.get_features(33.96, -5.27)
    jsonschema.validate(f, SCHEMA)
    v = f["vegetation"]
    assert v["status"] == "unavailable" and v["source"] is None and v["period"] is None
    assert v["ndvi_monthly"] == [None] * 12 and v["recent"] is None
    assert "ndvi_not_cached" in codes(f)
    assert "modis_ndvi" not in {s["id"] for s in f["sources"]}


def test_vegetation_from_warmed_cache(monkeypatch, power_raw, soil_raw):
    from data import ndvi
    import data.http
    from data.tests.test_ndvi import modis_fake

    install_fetcher(monkeypatch, power_raw, soil_raw)
    nasa_and_soil = data.http.fetch_json
    modis, _ = modis_fake()
    monkeypatch.setattr("data.http.fetch_json",
                        lambda url, **kw: (modis if "modis.ornl.gov" in url else nasa_and_soil)(url, **kw))
    ndvi.warm(33.96, -5.27, workers=2, log=lambda *_: None)
    f = pipeline.get_features(33.96, -5.27)
    jsonschema.validate(f, SCHEMA)
    v = f["vegetation"]
    assert v["status"] == "cache" and v["source"] == "modis_ndvi"
    assert v["period"] == {"start_year": ndvi.START_YEAR, "end_year": ndvi.END_YEAR}
    assert v["recent"]["year"] == ndvi.END_YEAR and len(v["recent"]["values"]) == 12
    assert {"ndvi_coarse_note", "ndvi_short_period"} <= codes(f)
    src = next(s for s in f["sources"] if s["id"] == "modis_ndvi")
    assert src["cache_status"] == "cache"
