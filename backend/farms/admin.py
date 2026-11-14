from django.contrib import admin

from .models import Field, Measurement, Result


@admin.register(Field)
class FieldAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'latitude', 'longitude')


@admin.register(Measurement)
class MeasurementAdmin(admin.ModelAdmin):
    list_display = ('field', 'date', 'temperature', 'rainfall')


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ('field', 'created_at')
