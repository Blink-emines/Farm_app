import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APITestCase

from .models import Field, Measurement, Result

User = get_user_model()


class ModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='amina', password='pw')
        self.field = Field.objects.create(
            owner=self.user, name='North field', latitude=33.57, longitude=-7.59
        )

    def test_field_belongs_to_its_owner(self):
        self.assertEqual(self.field.owner, self.user)
        self.assertEqual(list(self.user.fields.all()), [self.field])
        self.assertEqual(str(self.field), 'North field')

    def test_latitude_outside_the_globe_is_rejected(self):
        self.field.latitude = 91
        with self.assertRaises(ValidationError) as cm:
            self.field.full_clean()
        self.assertEqual(list(cm.exception.message_dict), ['latitude'])

    def test_longitude_outside_the_globe_is_rejected(self):
        self.field.longitude = -181
        with self.assertRaises(ValidationError) as cm:
            self.field.full_clean()
        self.assertEqual(list(cm.exception.message_dict), ['longitude'])

    def test_one_measurement_per_field_per_day(self):
        day = datetime.date(2026, 1, 15)
        Measurement.objects.create(
            field=self.field, date=day, temperature=14.2, rainfall=3.0
        )
        # atomic() keeps the failed save from breaking the test's transaction.
        with self.assertRaises(IntegrityError), transaction.atomic():
            Measurement.objects.create(
                field=self.field, date=day, temperature=15.0, rainfall=0.0
            )
        self.assertEqual(Measurement.objects.count(), 1)

    def test_measurement_values_may_be_missing(self):
        # NASA POWER has no value yet for the most recent days.
        m = Measurement.objects.create(
            field=self.field, date=datetime.date(2026, 1, 16)
        )
        self.assertIsNone(m.temperature)
        self.assertIsNone(m.rainfall)

    def test_result_stores_analysis_output(self):
        result = Result.objects.create(field=self.field, data={'heat_days': 4})
        result.refresh_from_db()
        self.assertEqual(result.data, {'heat_days': 4})
        self.assertIsNotNone(result.created_at)

    def test_deleting_a_field_deletes_its_measurements_and_results(self):
        Measurement.objects.create(field=self.field, date=datetime.date(2026, 1, 15))
        Result.objects.create(field=self.field, data={})
        self.field.delete()
        self.assertEqual(Measurement.objects.count(), 0)
        self.assertEqual(Result.objects.count(), 0)

    def test_deleting_a_user_deletes_their_fields(self):
        self.user.delete()
        self.assertEqual(Field.objects.count(), 0)


class AdminTests(TestCase):
    def test_models_are_visible_in_admin(self):
        admin_user = User.objects.create_superuser(username='boss', password='pw')
        self.client.force_login(admin_user)
        for model in ('field', 'measurement', 'result'):
            response = self.client.get(f'/admin/farms/{model}/')
            self.assertEqual(response.status_code, 200)


class AuthTests(APITestCase):
    def setUp(self):
        User.objects.create_user(username='amina', password='correct-horse-9')

    def test_login_returns_tokens(self):
        response = self.client.post(
            '/api/token/', {'username': 'amina', 'password': 'correct-horse-9'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_with_wrong_password_is_refused(self):
        response = self.client.post(
            '/api/token/', {'username': 'amina', 'password': 'wrong'}
        )
        self.assertEqual(response.status_code, 401)

    def test_refresh_token_gives_a_new_access_token(self):
        tokens = self.client.post(
            '/api/token/', {'username': 'amina', 'password': 'correct-horse-9'}
        ).data
        response = self.client.post('/api/token/refresh/', {'refresh': tokens['refresh']})
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)

    def test_endpoints_refuse_requests_without_a_token(self):
        for url in (
            '/api/',
            '/api/fields/',
            '/api/fields/1/',
            '/api/measurements/',
            '/api/measurements/1/',
        ):
            self.assertEqual(self.client.get(url).status_code, 401, url)
        self.assertEqual(self.client.post('/api/fields/', {}).status_code, 401)

    def test_endpoints_refuse_a_fake_token(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer not-a-real-token')
        self.assertEqual(self.client.get('/api/fields/').status_code, 401)

    def test_register_creates_a_user_who_can_log_in(self):
        response = self.client.post(
            '/api/register/', {'username': 'youssef', 'password': 'olive-tree-42'}
        )
        self.assertEqual(response.status_code, 201)
        self.assertNotIn('password', response.data)
        login = self.client.post(
            '/api/token/', {'username': 'youssef', 'password': 'olive-tree-42'}
        )
        self.assertEqual(login.status_code, 200)

    def test_register_rejects_a_taken_username(self):
        response = self.client.post(
            '/api/register/', {'username': 'amina', 'password': 'olive-tree-42'}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(User.objects.filter(username='amina').count(), 1)

    def test_register_rejects_a_weak_password(self):
        response = self.client.post(
            '/api/register/', {'username': 'youssef', 'password': '123'}
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(username='youssef').exists())

    def test_register_rejects_a_password_equal_to_the_username(self):
        response = self.client.post(
            '/api/register/', {'username': 'youssef123', 'password': 'youssef123'}
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(username='youssef123').exists())


class IsolationTests(APITestCase):
    """The golden rule: user A can never see or touch user B's data."""

    def setUp(self):
        day = datetime.date(2026, 1, 15)
        self.user_a = User.objects.create_user(username='a', password='correct-horse-9')
        self.user_b = User.objects.create_user(username='b', password='correct-horse-9')
        self.field_a = Field.objects.create(
            owner=self.user_a, name='A field', latitude=33.5, longitude=-7.5
        )
        self.field_b = Field.objects.create(
            owner=self.user_b, name='B field', latitude=34.0, longitude=-6.8
        )
        self.measurement_a = Measurement.objects.create(
            field=self.field_a, date=day, temperature=14.0, rainfall=1.0
        )
        self.measurement_b = Measurement.objects.create(
            field=self.field_b, date=day, temperature=16.0, rainfall=2.0
        )
        # Log in as A through the real login endpoint.
        token = self.client.post(
            '/api/token/', {'username': 'a', 'password': 'correct-horse-9'}
        ).data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_field_list_shows_only_my_fields(self):
        response = self.client.get('/api/fields/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([f['id'] for f in response.data], [self.field_a.id])

    def test_i_can_open_my_own_field(self):
        response = self.client.get(f'/api/fields/{self.field_a.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['name'], 'A field')

    def test_i_cannot_open_another_users_field(self):
        response = self.client.get(f'/api/fields/{self.field_b.id}/')
        self.assertEqual(response.status_code, 404)

    def test_i_cannot_edit_another_users_field(self):
        url = f'/api/fields/{self.field_b.id}/'
        self.assertEqual(self.client.patch(url, {'name': 'stolen'}).status_code, 404)
        self.assertEqual(
            self.client.put(
                url, {'name': 'stolen', 'latitude': 0, 'longitude': 0}
            ).status_code,
            404,
        )
        self.field_b.refresh_from_db()
        self.assertEqual(self.field_b.name, 'B field')

    def test_i_cannot_delete_another_users_field(self):
        response = self.client.delete(f'/api/fields/{self.field_b.id}/')
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Field.objects.filter(id=self.field_b.id).exists())

    def test_a_new_field_is_always_mine_even_if_i_name_another_owner(self):
        response = self.client.post(
            '/api/fields/',
            {'name': 'New', 'latitude': 30, 'longitude': -8, 'owner': self.user_b.id},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Field.objects.get(id=response.data['id']).owner, self.user_a)
        self.assertEqual(self.user_b.fields.count(), 1)

    def test_i_cannot_give_my_field_to_another_user(self):
        response = self.client.patch(
            f'/api/fields/{self.field_a.id}/', {'owner': self.user_b.id}
        )
        # Accepted, but the unknown 'owner' value is simply ignored.
        self.assertEqual(response.status_code, 200)
        self.field_a.refresh_from_db()
        self.assertEqual(self.field_a.owner, self.user_a)

    def test_i_can_edit_and_delete_my_own_field(self):
        url = f'/api/fields/{self.field_a.id}/'
        self.assertEqual(self.client.patch(url, {'name': 'Renamed'}).status_code, 200)
        self.field_a.refresh_from_db()
        self.assertEqual(self.field_a.name, 'Renamed')
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertFalse(Field.objects.filter(id=self.field_a.id).exists())

    def test_api_rejects_a_latitude_outside_the_globe(self):
        response = self.client.post(
            '/api/fields/', {'name': 'Bad', 'latitude': 91, 'longitude': 0}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('latitude', response.data)

    def test_measurement_list_shows_only_my_measurements(self):
        response = self.client.get('/api/measurements/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([m['id'] for m in response.data], [self.measurement_a.id])

    def test_i_cannot_open_another_users_measurement(self):
        response = self.client.get(f'/api/measurements/{self.measurement_b.id}/')
        self.assertEqual(response.status_code, 404)

    def test_measurements_are_read_only(self):
        response = self.client.post(
            '/api/measurements/',
            {'field': self.field_a.id, 'date': '2026-01-20', 'temperature': 1},
        )
        self.assertEqual(response.status_code, 405)
        url = f'/api/measurements/{self.measurement_a.id}/'
        self.assertEqual(self.client.delete(url).status_code, 405)
        self.assertEqual(Measurement.objects.count(), 2)
