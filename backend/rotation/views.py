"""Two open endpoints. Nothing is stored and no login is needed."""
import importlib
import logging
import threading

from rest_framework.exceptions import ParseError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .errors import error_for, error_response
from .validation import first_optimize_problem, first_request_problem, parse_coordinates

log = logging.getLogger(__name__)

# The solver (Pyomo + HiGHS) is not safe to run in two threads at once: a second request used to
# hang the whole server. Optimiser runs take about a second, so they simply wait their turn.
_OPTIMIZE_LOCK = threading.Lock()


class OpenView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]


class FeaturesView(OpenView):
    def get(self, request):
        coords = parse_coordinates(request.query_params)
        if coords is None:
            return error_response(
                400, 'invalid_coordinates',
                'Give lat and lon as numbers: lat between -90 and 90, lon between -180 and 180.')
        try:
            pipeline = importlib.import_module('data.pipeline')
            return Response(pipeline.get_features(*coords))
        except Exception as exc:
            log.exception('features failed')
            return error_for(exc)


class StrategiesView(OpenView):
    def post(self, request):
        try:
            body = request.data
        except ParseError:
            body = None
        problem = first_request_problem(body if isinstance(body, dict) else None)
        if problem:
            return error_response(400, 'invalid_request', problem)
        try:
            pipeline = importlib.import_module('data.pipeline')
            scorer = importlib.import_module('engine.scorer')
            features = pipeline.get_features(body['latitude'], body['longitude'])
            return Response(scorer.score(features, body))
        except Exception as exc:
            log.exception('strategies failed')
            return error_for(exc)


class OptimizeView(OpenView):
    def post(self, request):
        try:
            body = request.data
        except ParseError:
            body = None
        problem = first_optimize_problem(body)
        if problem:
            return error_response(400, 'invalid_request', problem)
        try:
            pipeline = importlib.import_module('data.pipeline')
            optimiser = importlib.import_module('engine.optimize')
            features = pipeline.get_features(body['latitude'], body['longitude'])
            with _OPTIMIZE_LOCK:
                return Response(optimiser.optimize(features, body))
        except Exception as exc:
            log.exception('optimize failed')
            return error_for(exc)
