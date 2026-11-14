import pytest

from data import bulk_download, cache, nasa_power
from data.errors import UpstreamUnavailable


def test_land_cells_come_from_raster_and_include_the_default_cells(rasters):
    merra, radiation = bulk_download.land_cells()
    assert (34.0, -5.0) in merra and (33.5, -5.5) in radiation
    assert len(merra) <= 4 and len(radiation) <= 2          # a 15 km patch touches few cells
    assert merra == sorted(merra)


@pytest.fixture
def small_job_list(monkeypatch):
    monkeypatch.setattr(bulk_download, "land_cells", lambda: ([(34.0, -5.0), (34.5, -5.0)], [(33.5, -5.5)]))
    monkeypatch.setattr(bulk_download.time, "sleep", lambda s: None)


def test_bulk_downloads_each_cell_once_and_is_resumable(small_job_list, monkeypatch, power_raw):
    calls = []

    def fake(url, **kw):
        calls.append(url)
        return power_raw

    monkeypatch.setattr("data.http.fetch_json", fake)
    assert bulk_download.main([]) == 0
    assert len(calls) == 3
    assert bulk_download.main([]) == 0           # second run: everything cached, nothing requested
    assert len(calls) == 3
    assert all(bulk_download.is_cached(j) for j in bulk_download.jobs())
    assert any(p.name.endswith(".json.gz") for p in cache.CACHE_DIR.iterdir())


def test_bulk_resumes_after_partial_run(small_job_list, monkeypatch, power_raw):
    calls = []
    monkeypatch.setattr("data.http.fetch_json", lambda url, **kw: calls.append(url) or power_raw)
    bulk_download.main(["--limit", "1"])
    assert len(calls) == 1
    bulk_download.main([])
    assert len(calls) == 3


def test_bulk_reports_failures_and_keeps_going(small_job_list, monkeypatch, power_raw, capsys):
    def flaky(url, **kw):
        if "latitude=34.500" in url:
            raise UpstreamUnavailable("down")
        return power_raw

    monkeypatch.setattr("data.http.fetch_json", flaky)
    assert bulk_download.main([]) == 1
    out = capsys.readouterr().out
    assert "FAILED 34.5,-5.0" in out and "2 downloaded, 1 failed" in out


def test_dry_run_downloads_nothing(small_job_list, monkeypatch, capsys):
    monkeypatch.setattr("data.http.fetch_json", lambda *a, **k: pytest.fail("no request expected"))
    assert bulk_download.main(["--dry-run"]) == 0
    assert "3 cells touch land" in capsys.readouterr().out
