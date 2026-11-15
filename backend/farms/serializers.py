from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from engine.loaders import load_crops

from .models import Farm, Field, Measurement, Result

# Crops a farmer can say are available locally (every engine crop except fallow).
MARKET_CROPS = [c for c in load_crops() if c != 'fallow']


CURRENT_CROPS = list(load_crops())  # every engine crop, 'fallow' = bare field


class FieldSerializer(serializers.ModelSerializer):
    current_crop = serializers.ChoiceField(choices=CURRENT_CROPS + [''], required=False)
    soil_type = serializers.ChoiceField(choices=[c for c, _ in Farm.SOIL_TYPES] + [''], required=False)
    crops = serializers.ListField(
        child=serializers.ChoiceField(choices=MARKET_CROPS), required=False, max_length=len(MARKET_CROPS)
    )

    class Meta:
        model = Field
        # No 'owner': the server sets it from the login token, never the client.
        fields = ['id', 'name', 'latitude', 'longitude', 'area_ha', 'current_crop', 'soil_type', 'crops']

    def validate_crops(self, crops):
        return list(dict.fromkeys(crops))


class ParcelSerializer(serializers.ModelSerializer):
    """One field of a farm, as entered in the setup wizard."""

    area_ha = serializers.FloatField(min_value=0.01, max_value=10000)

    class Meta:
        model = Field
        fields = ['id', 'name', 'area_ha', 'current_crop', 'soil_type', 'crops']
        read_only_fields = ['current_crop', 'soil_type', 'crops']


class FarmSerializer(serializers.ModelSerializer):
    parcels = ParcelSerializer(many=True)
    # Chosen later, in the optimisation tab; empty until then.
    crops = serializers.ListField(
        child=serializers.ChoiceField(choices=MARKET_CROPS), required=False, max_length=len(MARKET_CROPS)
    )

    class Meta:
        model = Farm
        # No 'owner': the server sets it from the login token, never the client.
        fields = ['id', 'name', 'latitude', 'longitude', 'soil_type', 'crops', 'parcels', 'created_at']
        read_only_fields = ['created_at']

    def validate_parcels(self, parcels):
        if not 1 <= len(parcels) <= 50:
            raise serializers.ValidationError('A farm has between 1 and 50 fields.')
        return parcels

    def validate_crops(self, crops):
        return list(dict.fromkeys(crops))  # drop duplicates, keep order

    def create(self, validated_data):
        parcels = validated_data.pop('parcels')
        farm = Farm.objects.create(**validated_data)
        # Each field sits at the farm's GPS point until the farmer places it more precisely.
        for parcel in parcels:
            Field.objects.create(
                owner=farm.owner, farm=farm, latitude=farm.latitude, longitude=farm.longitude, **parcel
            )
        return farm

    def update(self, farm, validated_data):
        # Fields are created with the farm; editing them here is not supported yet.
        if 'parcels' in validated_data:
            raise serializers.ValidationError({'parcels': 'Fields cannot be changed here.'})
        return super().update(farm, validated_data)


class MeasurementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Measurement
        fields = ['id', 'field', 'date', 'temperature', 'rainfall']


class ResultSerializer(serializers.ModelSerializer):
    """A saved plan: the request the farmer sent and the strategies they got back."""

    class Meta:
        model = Result
        fields = ['id', 'field', 'created_at', 'data']
        read_only_fields = ['created_at']

    def validate_field(self, field):
        # A plan can only be attached to one of your own fields.
        if field.owner != self.context['request'].user:
            raise serializers.ValidationError('Unknown field.')
        return field


class RegisterSerializer(serializers.ModelSerializer):
    # write_only: accepted on sign-up, never sent back in a response.
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=False, allow_blank=True)

    class Meta:
        model = get_user_model()
        fields = ['id', 'username', 'email', 'password']

    def validate_email(self, email):
        # Optional, but when given it must be unique so it can be used to log in.
        if email and get_user_model().objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError('This email is already used.')
        return email

    def validate(self, attrs):
        # Checked with the username so "too similar to the username" is caught.
        validate_password(attrs['password'], get_user_model()(username=attrs['username']))
        return attrs

    def create(self, validated_data):
        # create_user stores a hash of the password, not the password itself.
        return get_user_model().objects.create_user(**validated_data)


class LoginSerializer(TokenObtainPairSerializer):
    """Log in with a username or an email address, plus the password."""

    def validate(self, attrs):
        ident = attrs.get(self.username_field, '')
        if '@' in ident:
            user = get_user_model().objects.filter(email__iexact=ident).first()
            if user:
                attrs[self.username_field] = user.get_username()
        return super().validate(attrs)
