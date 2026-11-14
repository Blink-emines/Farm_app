import io
import json
import urllib.error
import urllib.request

import pytest

from data import cache, http, region
from data.errors import OutsidePilotRegion, UpstreamUnavailable


def test_rounding_to_two_decimals():
    assert region.round_point(33.9649, -5.2751) == (33.96, -5.28)


@pytest.mark.parametrize("lat,lon", [(33.96, -5.27), (20.70, -17.20), (35.95, -0.95), (30.43, -9.60)])
def test_inside_box_including_edges(lat, lon):
    region.check_in_pilot_region(lat, lon)


@pytest.mark.parametrize("lat,lon", [(36.20, -5.27), (33.96, -0.50), (20.69, -9.0), (33.96, -17.30), (0.0, 0.0), (48.85, 2.35)])
def test_outside_box_raises(lat, lon):
    with pytest.raises(OutsidePilotRegion):
        region.check_in_pilot_region(lat, lon)


class FakeResp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_fetch_json_ok(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: FakeResp(b'{"a": 1}'))
    assert http.fetch_json("https://example.org/x", timeout=1, retries=0) == {"a": 1}


def test_fetch_json_retries_then_succeeds(monkeypatch):
    calls = []

    def flaky(*a, **k):
        calls.append(1)
        if len(calls) == 1:
            raise urllib.error.URLError("boom")
        return FakeResp(b"{}")

    monkeypatch.setattr(urllib.request, "urlopen", flaky)
    monkeypatch.setattr(http.time, "sleep", lambda s: None)
    assert http.fetch_json("https://example.org/x", timeout=1, retries=1) == {}
    assert len(calls) == 2


@pytest.mark.parametrize("exc", [urllib.error.URLError("down"), TimeoutError("slow"),
                                 urllib.error.HTTPError("u", 503, "bad", {}, None)])
def test_fetch_json_errors_become_upstream_unavailable(monkeypatch, exc):
    def raiser(*a, **k):
        raise exc

    monkeypatch.setattr(urllib.request, "urlopen", raiser)
    monkeypatch.setattr(http.time, "sleep", lambda s: None)
    with pytest.raises(UpstreamUnavailable):
        http.fetch_json("https://example.org/x", timeout=1, retries=1)


def test_fetch_json_bad_json_is_upstream_unavailable(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: FakeResp(b"<html>"))
    with pytest.raises(UpstreamUnavailable):
        http.fetch_json("https://example.org/x", timeout=1, retries=0)


def test_cache_hit_never_repeats_request():
    calls = []

    def fetcher(url):
        calls.append(url)
        return {"v": len(calls)}

    p1 = [("latitude", "33.96"), ("longitude", "-5.27")]
    p2 = [("longitude", "-5.27"), ("latitude", "33.96")]  # same request, other order
    r1 = cache.cached_get("https://x.org/api", p1, fetcher)
    r2 = cache.cached_get("https://x.org/api", p2, fetcher)
    assert len(calls) == 1
    assert r1.status == "live" and r2.status == "cache"
    assert r1.response == r2.response == {"v": 1}
    assert r1.fetched_at == r2.fetched_at


def test_failed_request_is_not_cached():
    def bad(url):
        raise UpstreamUnavailable("down")

    with pytest.raises(UpstreamUnavailable):
        cache.cached_get("https://x.org/api", [("a", "1")], bad)
    assert cache.lookup("https://x.org/api", [("a", "1")]) is None


def test_cache_file_name_carries_coordinates():
    cache.cached_get("https://x.org/api", [("latitude", "33.96"), ("longitude", "-5.27")], lambda u: {})
    names = [p.name for p in cache.CACHE_DIR.iterdir()]
    assert len(names) == 1 and "_33.96_-5.27_" in names[0]
    saved = json.loads((cache.CACHE_DIR / names[0]).read_text())
    assert {"endpoint", "params", "fetched_at", "response"} <= set(saved)
