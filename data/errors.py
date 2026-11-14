"""Errors the data layer raises on purpose, so callers can turn them into HTTP codes."""


class DataError(Exception):
    """Base class for all data-layer errors."""


class OutsidePilotRegion(DataError):
    """The point is outside the Saiss pilot box."""


class UpstreamUnavailable(DataError):
    """NASA POWER (or another required source) could not be reached or gave unusable data."""
