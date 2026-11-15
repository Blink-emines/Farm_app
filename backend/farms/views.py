from rest_framework import generics, mixins, permissions, viewsets

from .models import Field, Measurement, Result
from .serializers import FieldSerializer, MeasurementSerializer, RegisterSerializer, ResultSerializer


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


class ResultViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """Save and read back the logged-in user's plans. Saved plans are not edited."""

    serializer_class = ResultSerializer

    def get_queryset(self):
        return Result.objects.filter(field__owner=self.request.user).order_by('-created_at')
