"""Region (all of Morocco, as defined by the user) and coordinate rounding.

The box is the first check. A point inside the box but over the sea has no SoilGrids land pixel;
pipeline.get_features rejects it the same way (no political boundary file is used)."""
from .errors import OutsidePilotRegion

REGION_NAME = "morocco"
LAT_MIN, LAT_MAX = 20.70, 35.95
LON_MIN, LON_MAX = -17.20, -0.95


def round_point(latitude, longitude):
    """Coordinates are rounded to 2 decimals before any fetch or cache lookup."""
    return round(float(latitude), 2), round(float(longitude), 2)


def check_in_pilot_region(latitude, longitude):
    if not (LAT_MIN <= latitude <= LAT_MAX and LON_MIN <= longitude <= LON_MAX):
        raise OutsidePilotRegion(
            f"Point {latitude}, {longitude} is outside the supported region, Morocco "
            f"(latitude {LAT_MIN} to {LAT_MAX}, longitude {LON_MIN} to {LON_MAX})."
        )
