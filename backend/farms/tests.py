import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

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
