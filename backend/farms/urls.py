from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('fields', views.FieldViewSet, basename='field')
router.register('measurements', views.MeasurementViewSet, basename='measurement')
router.register('results', views.ResultViewSet, basename='result')
router.register('farms', views.FarmViewSet, basename='farm')

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('tts/', views.TTSView.as_view(), name='tts'),
    *router.urls,
]
