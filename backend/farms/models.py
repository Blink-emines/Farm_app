from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Farm(models.Model):
    """The farm a user describes in the setup wizard: where it is, its soil, what can be grown."""

    SOIL_TYPES = [
        ('clay', 'Heavy clay (tirs)'),
        ('loam', 'Balanced soil'),
        ('sandy', 'Sandy (rmel)'),
        ('red', 'Red soil (hamri)'),
        ('stony', 'Stony or chalky'),
        ('unknown', 'Not known'),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='farms'
    )
    name = models.CharField(max_length=100)
    latitude = models.FloatField(
        validators=[MinValueValidator(-90), MaxValueValidator(90)]
    )
    longitude = models.FloatField(
        validators=[MinValueValidator(-180), MaxValueValidator(180)]
    )
    # Declared by the farmer. Not used by the scorer (it uses SoilGrids); kept for later.
    soil_type = models.CharField(max_length=10, choices=SOIL_TYPES, default='unknown')
    # Crop ids (engine/crops.yaml) the farmer can grow and buy seed for locally.
    crops = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Field(models.Model):
    """A piece of farmland that belongs to exactly one user."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='fields'
    )
    # Set when the field was created by the farm setup wizard.
    farm = models.ForeignKey(
        Farm, on_delete=models.CASCADE, related_name='parcels', null=True, blank=True
    )
    area_ha = models.FloatField(
        null=True, blank=True, validators=[MinValueValidator(0.01), MaxValueValidator(10000)]
    )
    # The farmer's answers in the optimisation tab, kept per field.
    current_crop = models.CharField(max_length=20, blank=True, default='')  # crop id, 'fallow' = bare
    soil_type = models.CharField(max_length=10, blank=True, default='')  # Farm.SOIL_TYPES, '' = farm's
    crops = models.JSONField(default=list, blank=True)  # crops the farmer can or wants to plant
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
