from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('fields', views.FieldViewSet, basename='field')
router.register('measurements', views.MeasurementViewSet, basename='measurement')

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    *router.urls,
]
