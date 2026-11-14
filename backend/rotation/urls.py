from django.urls import path

from . import views

urlpatterns = [
    path('features', views.FeaturesView.as_view(), name='rotation-features'),
    path('optimize', views.OptimizeView.as_view(), name='rotation-optimize'),
    path('strategies', views.StrategiesView.as_view(), name='rotation-strategies'),
]
