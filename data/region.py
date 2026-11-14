"""Pilot region (Saiss box) and coordinate rounding."""
from .errors import OutsidePilotRegion

LAT_MIN, LAT_MAX = 33.70, 34.20
LON_MIN, LON_MAX = -5.70, -4.70


def round_point(latitude, longitude):
    """Coordinates are rounded to 2 decimals before any fetch or cache lookup."""
    return round(float(latitude), 2), round(float(longitude), 2)


def check_in_pilot_region(latitude, longitude):
    if not (LAT_MIN <= latitude <= LAT_MAX and LON_MIN <= longitude <= LON_MAX):
        raise OutsidePilotRegion(
            f"Point {latitude}, {longitude} is outside the Saiss pilot region "
            f"(latitude {LAT_MIN} to {LAT_MAX}, longitude {LON_MIN} to {LON_MAX})."
        )
