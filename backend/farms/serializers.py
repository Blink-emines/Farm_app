from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Field, Measurement


class FieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = Field
        # No 'owner': the server sets it from the login token, never the client.
        fields = ['id', 'name', 'latitude', 'longitude']


class MeasurementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Measurement
        fields = ['id', 'field', 'date', 'temperature', 'rainfall']


class RegisterSerializer(serializers.ModelSerializer):
    # write_only: accepted on sign-up, never sent back in a response.
    password = serializers.CharField(write_only=True)

    class Meta:
        model = get_user_model()
        fields = ['id', 'username', 'password']

    def validate(self, attrs):
        # Checked with the username so "too similar to the username" is caught.
        validate_password(attrs['password'], get_user_model()(username=attrs['username']))
        return attrs

    def create(self, validated_data):
        # create_user stores a hash of the password, not the password itself.
        return get_user_model().objects.create_user(**validated_data)
