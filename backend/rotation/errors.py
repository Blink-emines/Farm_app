"""One error shape for the whole rotation API: {"error": {"code", "message"}}."""
from rest_framework.response import Response


def error_response(status, code, message):
    return Response({'error': {'code': code, 'message': message}}, status=status)


# Exceptions from data/errors.py are matched by class name so this app does not
# need data/ to exist just to load.
KNOWN_ERRORS = {
    'OutsidePilotRegion': (
        422, 'outside_pilot_region',
        'This point is outside the covered area (Morocco, latitude 20.70 to 35.95, longitude -17.20 to -0.95) or not on land.',
    ),
    'UpstreamUnavailable': (
        502, 'upstream_unavailable',
        'The weather or soil service is not answering right now. Try again later.',
    ),
}


def error_for(exc):
    """Turn an exception from data/ or engine/ into an error response."""
    for cls in type(exc).__mro__:
        if cls.__name__ in KNOWN_ERRORS:
            return error_response(*KNOWN_ERRORS[cls.__name__])
    return error_response(500, 'internal_error', 'Something went wrong on our side. Try again later.')
