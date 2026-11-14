import pytest

from data import cache, ndvi
from data.errors import UpstreamUnavailable


def resp(items):
    return {"subset": [{"modis_date": m, "calendar_date": c, "data": [v]} for m, c, v in items]}


def test_request_plan_respects_service_limit():
    dates = ndvi.modis_dates()
    assert len(dates) == 23 * (ndvi.END_YEAR - ndvi.START_YEAR + 1)
    assert dates[0] == f"A{ndvi.START_YEAR}001" and dates[1] == f"A{ndvi.START_YEAR}017"
    assert dates[22] == f"A{ndvi.START_YEAR}353" and dates[23] == f"A{ndvi.START_YEAR + 1}001"
    plan = ndvi.chunks()
    covered = sum(dates.index(e) - dates.index(s) + 1 for s, e in plan)
    assert covered == len(dates) and all(dates.index(e) - dates.index(s) + 1 <= 10 for s, e in plan)


def test_clean_series_scales_and_drops_bad_pixels():
    n = ndvi.parse_chunk(resp([
        ("A2024001", "2024-01-01", 4349),    # good
        ("A2024017", "2024-01-17", -3000),   # fill value
        ("A2024033", "2024-02-02", 5000),    # cloudy (reliability 3)
        ("A2024049", "2024-02-18", 6000),    # marginal (1): kept
        ("A2024065", "2024-03-05", 12000),   # outside valid range
        ("A2024081", "2024-03-21", 7000),    # snow/ice (2)
        ("A2024097", "2024-04-06", None),
    ]))
    r = ndvi.parse_chunk(resp([
        ("A2024001", "2024-01-01", 0), ("A2024017", "2024-01-17", 0), ("A2024033", "2024-02-02", 3),
        ("A2024049", "2024-02-18", 1), ("A2024065", "2024-03-05", 0), ("A2024081", "2024-03-21", 2),
        ("A2024097", "2024-04-06", 0),
    ]))
    assert ndvi.clean_series(n, r) == {"2024-01-01": pytest.approx(0.4349), "2024-02-18": pytest.approx(0.6)}


def test_missing_reliability_drops_the_value():
    n = ndvi.parse_chunk(resp([("A2024001", "2024-01-01", 4000)]))
    assert ndvi.clean_series(n, {}) == {}


def test_monthly_uses_midpoint_and_recent_is_last_year(monkeypatch):
    monkeypatch.setattr(ndvi, "END_YEAR", 2024)
    series = {"2023-01-01": 0.4, "2024-01-01": 0.6, "2024-01-25": 0.8, "2024-02-02": 0.5}
    # mid-points: 2023-01-09 (Jan), 2024-01-09 (Jan), 2024-02-02 (Feb), 2024-02-10 (Feb)
    monthly, recent = ndvi.monthly_values(series)
    assert monthly[0] == pytest.approx((0.4 + 0.6) / 2)   # mean of year means for January
    assert monthly[1] == pytest.approx(0.65)
    assert monthly[5] is None
    assert recent["year"] == 2024 and recent["values"][0] == pytest.approx(0.6)


def test_nothing_valid_is_unavailable():
    with pytest.raises(ndvi.NdviUnavailable) as e:
        ndvi.monthly_values({})
    assert e.value.code == "ndvi_unavailable"


def test_load_without_cache_does_not_use_network():
    with pytest.raises(ndvi.NdviUnavailable) as e:
        ndvi.load(33.96, -5.27, allow_network=False)
    assert e.value.code == "ndvi_not_cached"


def modis_fake(fail=False):
    """A stand-in for http.fetch_json that answers MODIS requests; returns (function, list of urls)."""
    calls = []

    def fake(url, **kw):
        calls.append(url)
        if fail:
            raise UpstreamUnavailable("503")
        band = "pixel_reliability" in url
        start = url.split("startDate=")[1].split("&")[0]
        end = url.split("endDate=")[1].split("&")[0]
        items = []
        for m in ndvi.modis_dates():
            if start <= m <= end:
                year, doy = int(m[1:5]), int(m[5:])
                cal = f"{year}-{1 + (doy - 1) // 31:02d}-15" if doy < 360 else f"{year}-12-15"
                items.append((m, cal, 0 if band else 5000))
        return resp(items)

    return fake, calls


def fake_service(monkeypatch, fail=False):
    fake, calls = modis_fake(fail)
    monkeypatch.setattr("data.http.fetch_json", fake)
    return calls


def test_warm_then_load_from_cache_only(monkeypatch):
    calls = fake_service(monkeypatch)
    ndvi.warm(33.96, -5.27, workers=2, log=lambda *_: None)
    assert len(calls) == 2 * len(ndvi.chunks())
    got = ndvi.load(33.96, -5.27, allow_network=False)
    assert got["status"] == "cache" and len(calls) == 2 * len(ndvi.chunks())  # no repeated request
    assert any(v == pytest.approx(0.5) for v in got["ndvi_monthly"] if v is not None)


def test_service_failure_becomes_ndvi_unavailable(monkeypatch):
    fake_service(monkeypatch, fail=True)
    with pytest.raises(ndvi.NdviUnavailable) as e:
        ndvi.load(33.96, -5.27, allow_network=True)
    assert e.value.code == "ndvi_unavailable"
    assert cache.lookup(ndvi.ENDPOINT, ndvi._params(33.96, -5.27, ndvi.NDVI_BAND, *ndvi.chunks()[0])) is None
