"""get_features(latitude, longitude): the one function the rest of the app calls."""
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import jsonschema

import rasterio.errors

from . import climatology, nasa_power, ndvi, region, soil_raster, soilgrids
from .errors import OutsidePilotRegion, UpstreamUnavailable

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "docs" / "contracts" / "features.schema.json"

# name -> (unit, method, NASA parameter(s) or None)
SERIES = {
    "t2m_mean": ("°C", "monthly mean of daily T2M, averaged over the period", "T2M"),
    "t2m_max": ("°C", "monthly mean of daily T2M_MAX, averaged over the period", "T2M_MAX"),
    "t2m_min": ("°C", "monthly mean of daily T2M_MIN, averaged over the period", "T2M_MIN"),
    "precipitation": ("mm/month", "monthly sum of daily PRECTOTCORR, averaged over the period", "PRECTOTCORR"),
    "et0": ("mm/month",
            "FAO-56 Penman-Monteith computed per day (G=0, wind used as given at 2 m, es from Tmax/Tmin, "
            "ea from mean RH), summed per month, averaged over the period",
            "T2M,T2M_MAX,T2M_MIN,RH2M,WS2M,ALLSKY_SFC_SW_DWN"),
    "water_balance": ("mm/month", "precipitation minus et0, per month and year, averaged over the period", None),
    "rh2m": ("%", "monthly mean of daily RH2M, averaged over the period", "RH2M"),
    "ws2m": ("m/s", "monthly mean of daily WS2M, averaged over the period", "WS2M"),
    "solar_radiation": ("MJ/m²/day", "monthly mean of daily ALLSKY_SFC_SW_DWN (MJ/m^2/day for community AG), "
                                     "averaged over the period", "ALLSKY_SFC_SW_DWN"),
    "root_zone_wetness": ("0-1", "monthly mean of daily GWETROOT, averaged over the period", "GWETROOT"),
    "frost_days": ("days/month", "days with daily T2M_MIN below 0 °C, counted per month, averaged over the period",
                   "T2M_MIN"),
}

GAP_MESSAGES = {
    "climate_coarse_grid": "NASA POWER is satellite/model data on a coarse grid (about 50 km), so all "
                           "fields in the same cell get the same climate. It is not a weather-station record.",
    "root_zone_wetness_model": "Root-zone wetness is a satellite/model estimate, not a measurement in your field.",
    "soil_model_estimate": "SoilGrids values are 250 m model estimates, not a soil test; check with a "
                           "local soil analysis.",
    "soil_nearest_pixel": "There is no soil value exactly at this point (town, water or edge pixel); the nearest "
                          "SoilGrids pixel within about 3 km was used.",
    "soil_fallback_used": "SoilGrids could not be reached, so soil values come from a saved response for "
                          "the default point (33.96, -5.27), not for this exact location.",
    "soil_unavailable": "No soil data could be obtained (SoilGrids unreachable and no saved copy).",
    "soil_missing_values": "SoilGrids has no value for some soil properties or depths at this point.",
    "ndvi_unavailable": "Satellite greenness (NDVI) could not be obtained from the NASA MODIS service; "
                        "NDVI values are empty (null).",
    "ndvi_not_cached": "Satellite greenness (NDVI) for this point has not been downloaded yet (the NASA MODIS "
                       "service is slow), so NDVI values are empty (null).",
    "ndvi_coarse_note": "NDVI comes from a 250 m satellite pixel that may mix crops, trees and bare soil, "
                        "with cloudy observations removed; it shows how green the area looks, not your exact field.",
    "ndvi_short_period": "NDVI is averaged over only 5 years (2020-2024) because the NASA MODIS service is "
                         "slow, so it is less stable than the 20-year climate values.",
    "climate_missing_values": "Some daily NASA POWER values were missing; affected months were averaged "
                              "from fewer days or are empty (null).",
}


def _source(source_id, name, dataset, url, accessed_at, cache_status):
    return {"id": source_id, "name": name, "dataset": dataset, "url": url,
            "accessed_at": accessed_at, "cache_status": cache_status}


def _gap(code, affects):
    return {"code": code, "message": GAP_MESSAGES[code], "affects": affects}


def _load_soil(latitude, longitude):
    """Return (status, layers, source_or_None, extra gap codes).

    Order: local SoilGrids rasters, then the REST service (cached), then the saved fallback.
    Raises OutsidePilotRegion when the rasters say there is no land pixel (sea).
    Soil problems other than that never raise."""
    if soil_raster.available():
        try:
            layers, nearest = soil_raster.lookup(latitude, longitude)
        except soil_raster.NoLandPixel:
            raise OutsidePilotRegion(
                f"Point {latitude}, {longitude} has no SoilGrids land pixel (sea or outside the data).")
        except (rasterio.errors.RasterioError, OSError):
            pass  # damaged raster: use the REST service below
        else:
            src = _source("soilgrids", "ISRIC SoilGrids",
                          "SoilGrids 2.0 mean, 250 m rasters from the official WCS, local copy; 0-5/5-15/15-30 cm",
                          "https://maps.isric.org/", soil_raster.fetched_at(), "cache")
            return "cache", layers, src, (["soil_nearest_pixel"] if nearest else [])
    attempts = []
    try:
        got = soilgrids.fetch(latitude, longitude)
        attempts.append((got.response, got.fetched_at, got.status))
    except UpstreamUnavailable:
        pass
    saved = soilgrids.load_fallback()
    if saved:
        attempts.append((saved[0], saved[1], "fallback"))
    for response, fetched_at, status in attempts:
        try:
            layers = soilgrids.parse_layers(response)
        except soilgrids.SoilParseError:
            continue
        if layers:
            src = _source("soilgrids", "ISRIC SoilGrids",
                          "SoilGrids 2.0 point query, mean, 0-5/5-15/15-30 cm", soilgrids.ENDPOINT,
                          fetched_at, status)
            return status, layers, src, []
    return "unavailable", [], None, []


def _load_vegetation(latitude, longitude):
    """Return (vegetation block, source_or_None, gap codes). Never raises for NDVI problems."""
    try:
        got = ndvi.load(latitude, longitude)
    except ndvi.NdviUnavailable as exc:
        block = {"status": "unavailable", "source": None, "product": ndvi.PRODUCT, "period": None,
                 "ndvi_monthly": [None] * 12, "recent": None}
        return block, None, [exc.code]
    block = {"status": got["status"], "source": "modis_ndvi", "product": ndvi.PRODUCT,
             "period": {"start_year": ndvi.START_YEAR, "end_year": ndvi.END_YEAR},
             "ndvi_monthly": got["ndvi_monthly"], "recent": got["recent"]}
    src = _source("modis_ndvi", "NASA MODIS (via ORNL DAAC MODIS web service)",
                  "MOD13Q1 250 m 16-day NDVI, single pixel at the point, pixel reliability 0-1 only",
                  ndvi.BASE_URL, got["fetched_at"], got["status"])
    codes = ["ndvi_coarse_note"]
    if ndvi.END_YEAR - ndvi.START_YEAR + 1 < 20:
        codes.append("ndvi_short_period")
    return block, src, codes


def get_features(latitude, longitude):
    """Return a dict valid against features.schema.json.

    Raises OutsidePilotRegion or UpstreamUnavailable (NASA POWER unreachable and not cached)."""
    lat, lon = region.round_point(latitude, longitude)
    if not (math.isfinite(lat) and math.isfinite(lon)):
        raise ValueError("latitude and longitude must be finite numbers")
    region.check_in_pilot_region(lat, lon)

    soil_status, layers, soil_source, soil_codes = _load_soil(lat, lon)   # sea points stop here

    df, elevation, fetched_at, power_status = nasa_power.fetch_daily(lat, lon)
    monthly = climatology.monthly_climatology(df, lat, elevation)

    series = {
        name: {"values": monthly[name], "unit": unit, "source": "nasa_power",
               "method": method, "nasa_parameter": param}
        for name, (unit, method, param) in SERIES.items()
    }
    series["heat_days"] = {
        str(t): {"values": monthly["heat_days"][str(t)], "unit": "days/month", "source": "nasa_power",
                 "method": f"days with daily T2M_MAX above {t} °C, counted per month, averaged over the period",
                 "nasa_parameter": "T2M_MAX"}
        for t in climatology.HEAT_THRESHOLDS
    }

    vegetation, ndvi_source, ndvi_codes = _load_vegetation(lat, lon)
    yearly = climatology.yearly_series(df, lat, elevation)
    yearly.update({
        "source": "nasa_power",
        "method": "per calendar year from daily values: sums of PRECTOTCORR and FAO-56 ET0, "
                  "days with T2M_MIN < 0 °C, days with T2M_MAX > 35 °C; null if the year has a missing day",
    })

    sources = [_source("nasa_power", "NASA POWER", "NASA POWER daily point API, community AG",
                       nasa_power.ENDPOINT, fetched_at, power_status)]
    if soil_source:
        sources.append(soil_source)
    if ndvi_source:
        sources.append(ndvi_source)

    null_paths = [f"climate.monthly.{n}" for n, s in series.items()
                  if n != "heat_days" and None in s["values"]]
    null_paths += [f"climate.monthly.heat_days.{t}" for t, s in series["heat_days"].items()
                   if None in s["values"]]
    gaps = [_gap("climate_coarse_grid", ["climate"]),
            _gap("root_zone_wetness_model", ["climate.monthly.root_zone_wetness"])]
    if null_paths or df.isna().any().any():
        gaps.append(_gap("climate_missing_values", null_paths or ["climate.monthly"]))
    if soil_status == "unavailable":
        gaps.append(_gap("soil_unavailable", ["soil"]))
    else:
        gaps.append(_gap("soil_model_estimate", ["soil"]))
        gaps += [_gap(code, ["soil"]) for code in soil_codes]
        if soil_status == "fallback":
            gaps.append(_gap("soil_fallback_used", ["soil"]))
        if any(v is None for layer in layers for v in layer.values()):
            gaps.append(_gap("soil_missing_values", ["soil.layers"]))

    gaps += [_gap(code, ["vegetation"]) for code in ndvi_codes]

    features = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "location": {"latitude": lat, "longitude": lon,
                     "elevation_m": None if elevation is None else round(elevation, 2), "region": region.REGION_NAME},
        "climate": {"period": {"start_year": nasa_power.START_YEAR, "end_year": nasa_power.END_YEAR},
                    "monthly": series},
        "yearly": yearly,
        "vegetation": vegetation,
        "soil": {"status": soil_status, "source": "soilgrids" if soil_source else None, "layers": layers},
        "data_gaps": gaps,
        "sources": sources,
    }
    jsonschema.validate(features, json.loads(SCHEMA_PATH.read_text()))
    return features
