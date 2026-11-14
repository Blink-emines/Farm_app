from django.urls import path

from . import views

urlpatterns = [
    path('features', views.FeaturesView.as_view(), name='rotation-features'),
    path('strategies', views.StrategiesView.as_view(), name='rotation-strategies'),
]
