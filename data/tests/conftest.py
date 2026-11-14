"""Shared test setup: no test may reach the network, and every test gets its own empty cache."""
import json
import urllib.request
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("test tried to use the network")

    monkeypatch.setattr(urllib.request, "urlopen", blocked)


@pytest.fixture(autouse=True)
def tmp_cache(tmp_path, monkeypatch):
    from data import cache

    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path / "cache")
    return tmp_path / "cache"


@pytest.fixture
def power_raw():
    return json.loads((FIXTURES / "power_daily_2023_2024.json").read_text())


@pytest.fixture
def soil_raw():
    return json.loads((FIXTURES / "soilgrids_default.json").read_text())
