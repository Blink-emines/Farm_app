"""data.pipeline and engine.scorer are replaced by fakes: these tests check only the HTTP layer."""
import sys
import types
from unittest import mock

from django.test import SimpleTestCase
from rest_framework.test import APIClient


class OutsidePilotRegion(Exception):
    pass


class UpstreamUnavailable(Exception):
    pass


GOOD_BODY = {
    'latitude': 33.96,
    'longitude': -5.27,
    'current_rotation': {'seasons': [{'crop_id': 'wheat'}, {'crop_id': 'fallow', 'sow_month': 10}]},
    'priorities': {'save_water': 3, 'improve_soil': 0, 'extra_income': 5, 'reduce_erosion': 1, 'forage': 2},
}


class ApiTestCase(SimpleTestCase):
    def setUp(self):
        self.get_features = mock.Mock(return_value={'fake': 'features'})
        self.score = mock.Mock(return_value={'fake': 'strategies'})
        pipeline = types.ModuleType('data.pipeline')
        pipeline.get_features = self.get_features
        scorer = types.ModuleType('engine.scorer')
        scorer.score = self.score
        patcher = mock.patch.dict(sys.modules, {
            'data': types.ModuleType('data'), 'data.pipeline': pipeline,
            'engine': types.ModuleType('engine'), 'engine.scorer': scorer,
        })
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = APIClient()

    def assert_error(self, response, status, code):
        self.assertEqual(response.status_code, status)
        self.assertEqual(set(response.json()), {'error'})
        self.assertEqual(set(response.json()['error']), {'code', 'message'})
        self.assertEqual(response.json()['error']['code'], code)
        self.assertTrue(response.json()['error']['message'])


class FeaturesEndpointTests(ApiTestCase):
    def test_success_returns_features_and_needs_no_login(self):
        r = self.client.get('/api/features', {'lat': '33.96', 'lon': '-5.27'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {'fake': 'features'})
        self.get_features.assert_called_once_with(33.96, -5.27)

    def test_bad_coordinates_are_400(self):
        for params in ({}, {'lat': '33.9'}, {'lat': 'abc', 'lon': '1'}, {'lat': '91', 'lon': '0'},
                       {'lat': '0', 'lon': '181'}, {'lat': 'nan', 'lon': '0'}, {'lat': 'inf', 'lon': '0'}):
            with self.subTest(params=params):
                self.assert_error(self.client.get('/api/features', params), 400, 'invalid_coordinates')
        self.get_features.assert_not_called()

    def test_outside_region_is_422(self):
        self.get_features.side_effect = OutsidePilotRegion('x')
        self.assert_error(self.client.get('/api/features', {'lat': '10', 'lon': '10'}), 422, 'outside_pilot_region')

    def test_upstream_is_502(self):
        self.get_features.side_effect = UpstreamUnavailable('x')
        self.assert_error(self.client.get('/api/features', {'lat': '33.9', 'lon': '-5.2'}), 502, 'upstream_unavailable')

    def test_unexpected_error_is_500_without_details(self):
        self.get_features.side_effect = RuntimeError('secret path /etc/x')
        r = self.client.get('/api/features', {'lat': '33.9', 'lon': '-5.2'})
        self.assert_error(r, 500, 'internal_error')
        self.assertNotIn('secret', r.content.decode())


class StrategiesEndpointTests(ApiTestCase):
    def post(self, body):
        return self.client.post('/api/strategies', body, format='json')

    def test_success_calls_pipeline_then_scorer(self):
        r = self.post(GOOD_BODY)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {'fake': 'strategies'})
        self.get_features.assert_called_once_with(33.96, -5.27)
        self.score.assert_called_once_with({'fake': 'features'}, GOOD_BODY)

    def test_invalid_bodies_are_400(self):
        bad = {k: v for k, v in GOOD_BODY.items() if k != 'priorities'}
        cases = {
            'missing priorities': bad,
            'no seasons': {**GOOD_BODY, 'current_rotation': {'seasons': []}},
            'seven seasons': {**GOOD_BODY, 'current_rotation': {'seasons': [{'crop_id': 'wheat'}] * 7}},
            'unknown crop': {**GOOD_BODY, 'current_rotation': {'seasons': [{'crop_id': 'rice'}]}},
            'priority too high': {**GOOD_BODY, 'priorities': {**GOOD_BODY['priorities'], 'forage': 6}},
            'extra field': {**GOOD_BODY, 'extra': 1},
            'latitude text': {**GOOD_BODY, 'latitude': 'north'},
            'list instead of object': [1, 2],
        }
        for name, body in cases.items():
            with self.subTest(name):
                self.assert_error(self.post(body), 400, 'invalid_request')
        self.get_features.assert_not_called()
        self.score.assert_not_called()

    def test_malformed_json_is_400(self):
        r = self.client.post('/api/strategies', 'not json', content_type='application/json')
        self.assert_error(r, 400, 'invalid_request')

    def test_outside_region_is_422(self):
        self.get_features.side_effect = OutsidePilotRegion('x')
        self.assert_error(self.post(GOOD_BODY), 422, 'outside_pilot_region')

    def test_upstream_is_502(self):
        self.score.side_effect = UpstreamUnavailable('x')
        self.assert_error(self.post(GOOD_BODY), 502, 'upstream_unavailable')

    def test_unexpected_error_is_500(self):
        self.score.side_effect = ValueError('boom')
        self.assert_error(self.post(GOOD_BODY), 500, 'internal_error')
