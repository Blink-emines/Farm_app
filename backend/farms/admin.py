from django.contrib import admin

from .models import Farm, Field, Measurement, Result


@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'soil_type', 'latitude', 'longitude', 'created_at')


@admin.register(Field)
class FieldAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'farm', 'area_ha', 'latitude', 'longitude')


@admin.register(Measurement)
class MeasurementAdmin(admin.ModelAdmin):
    list_display = ('field', 'date', 'temperature', 'rainfall')


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ('field', 'created_at')
