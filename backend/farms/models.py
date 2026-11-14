from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Field(models.Model):
    """A piece of farmland that belongs to exactly one user."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='fields'
    )
    name = models.CharField(max_length=100)
    latitude = models.FloatField(
        validators=[MinValueValidator(-90), MaxValueValidator(90)]
    )
    longitude = models.FloatField(
        validators=[MinValueValidator(-180), MaxValueValidator(180)]
    )

    def __str__(self):
        return self.name


class Measurement(models.Model):
    """One day of weather for one field, fetched from NASA POWER."""

    field = models.ForeignKey(
        Field, on_delete=models.CASCADE, related_name='measurements'
    )
    date = models.DateField()
    # Null when NASA POWER has no value for that day (typical for recent days).
    temperature = models.FloatField(null=True, blank=True)  # °C, daily average
    rainfall = models.FloatField(null=True, blank=True)  # mm per day

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['field', 'date'], name='one_measurement_per_field_per_day'
            )
        ]

    def __str__(self):
        return f'{self.field} on {self.date}'


class Result(models.Model):
    """The output of one pandas analysis run for one field."""

    field = models.ForeignKey(Field, on_delete=models.CASCADE, related_name='results')
    created_at = models.DateTimeField(auto_now_add=True)
    data = models.JSONField()

    def __str__(self):
        return f'Result for {self.field} ({self.created_at:%Y-%m-%d})'
