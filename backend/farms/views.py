from rest_framework import generics, permissions, viewsets

from .models import Field, Measurement
from .serializers import FieldSerializer, MeasurementSerializer, RegisterSerializer


class RegisterView(generics.CreateAPIView):
    """Sign up. The only endpoint open to people who are not logged in."""

    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class FieldViewSet(viewsets.ModelViewSet):
    """List, create, edit and delete the logged-in user's fields."""

    serializer_class = FieldSerializer

    def get_queryset(self):
        # Golden rule: only this user's fields exist as far as they can tell.
        return Field.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class MeasurementViewSet(viewsets.ReadOnlyModelViewSet):
    """Read the weather measurements of the logged-in user's fields."""

    serializer_class = MeasurementSerializer

    def get_queryset(self):
        return Measurement.objects.filter(field__owner=self.request.user)
