"""Shared test setup: no test may reach the network, and every test gets its own empty cache."""
import json
import urllib.request
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import transform

FIXTURES = Path(__file__).parent / "fixtures"
LAT, LON = 33.96, -5.27


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


@pytest.fixture(autouse=True)
def no_real_rasters(tmp_path, monkeypatch):
    """Tests never read the real (large, gitignored) SoilGrids rasters; the `rasters` fixture makes tiny ones."""
    from data import soil_raster

    monkeypatch.setattr(soil_raster, "RASTER_DIR", tmp_path / "no_rasters")
    soil_raster._open.cache_clear()


@pytest.fixture
def power_raw():
    return json.loads((FIXTURES / "power_daily_2023_2024.json").read_text())


@pytest.fixture
def soil_raw():
    return json.loads((FIXTURES / "soilgrids_default.json").read_text())


@pytest.fixture
def rasters(tmp_path, monkeypatch):
    from data import soil_raster
    """15 tiny rasters (60x60 px of 250 m) around the default point; 0 = no data like the real WCS files."""
    x, y = transform("EPSG:4326", soil_raster.IGH, [LON], [LAT])
    left, top = round(x[0] / 250) * 250 - 7500, round(y[0] / 250) * 250 + 7500
    base = {"clay": 361, "sand": 275, "silt": 363, "soc": 262, "phh2o": 80}
    monkeypatch.setattr(soil_raster, "RASTER_DIR", tmp_path)
    soil_raster._open.cache_clear()
    for i, depth in enumerate(soil_raster.DEPTHS):
        for prop, value in base.items():
            data = np.full((60, 60), value + i, dtype="int16")
            with rasterio.open(soil_raster.layer_path(prop, depth), "w", driver="GTiff", height=60, width=60,
                               count=1, dtype="int16", crs=soil_raster.IGH,
                               transform=from_origin(left, top, 250, 250)) as ds:
                ds.write(data, 1)
    (tmp_path / "manifest.json").write_text(json.dumps({"fetched_at": "2026-11-14T16:00:00Z"}))
    return tmp_path


