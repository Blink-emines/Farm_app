import pytest
import rasterio
from rasterio.warp import transform

from data import soil_raster

from data.tests.conftest import LAT, LON


def punch_hole(path, row, col, radius=0):
    with rasterio.open(path, "r+") as ds:
        a = ds.read(1)
        a[row - radius:row + radius + 1, col - radius:col + radius + 1] = 0
        ds.write(a, 1)
    soil_raster._open.cache_clear()


def point_pixel():
    ds = soil_raster._open(str(soil_raster.layer_path("clay", "0-5cm")))
    x, y = transform("EPSG:4326", soil_raster.IGH, [LON], [LAT])
    return ds.index(x[0], y[0])


def test_available_needs_all_layers_and_manifest(rasters):
    assert soil_raster.available()
    soil_raster.layer_path("soc", "5-15cm").unlink()
    assert not soil_raster.available()


def test_lookup_converts_units_like_the_rest_service(rasters):
    layers, nearest = soil_raster.lookup(LAT, LON)
    assert nearest is False
    assert [l["depth"] for l in layers] == ["0-5cm", "5-15cm", "15-30cm"]
    assert layers[0] == {"depth": "0-5cm", "clay_pct": 36.1, "sand_pct": 27.5, "silt_pct": 36.3,
                         "soc_g_kg": 26.2, "ph_h2o": 8.0}
    assert layers[2]["clay_pct"] == pytest.approx(36.3)   # value + 2 in the fixture, / 10
    assert soil_raster.fetched_at() == "2026-11-14T16:00:00Z"


def test_no_data_pixel_uses_nearest_valid_pixel(rasters):
    row, col = point_pixel()
    punch_hole(soil_raster.layer_path("clay", "0-5cm"), row, col, radius=1)
    layers, nearest = soil_raster.lookup(LAT, LON)
    assert nearest is True and layers[0]["clay_pct"] == 36.1


def test_sea_point_raises_no_land_pixel(rasters):
    row, col = point_pixel()
    punch_hole(soil_raster.layer_path("clay", "0-5cm"), row, col, radius=soil_raster.SEARCH_RADIUS_PX + 1)
    with pytest.raises(soil_raster.NoLandPixel):
        soil_raster.lookup(LAT, LON)


def test_point_outside_the_raster_raises(rasters):
    with pytest.raises(soil_raster.NoLandPixel):
        soil_raster.lookup(30.0, -9.0)


def test_zero_in_one_layer_is_null_not_zero(rasters):
    row, col = point_pixel()
    punch_hole(soil_raster.layer_path("soc", "5-15cm"), row, col)
    layers, _ = soil_raster.lookup(LAT, LON)
    assert layers[1]["soc_g_kg"] is None and layers[0]["soc_g_kg"] == 26.2
