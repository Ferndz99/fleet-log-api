# apps/accounts/profile/api/serializers.py

from rest_framework import serializers
from apps.accounts.profile.domain.models import Profile
from django.utils.translation import gettext_lazy as _


class ProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Profile
        fields = [
            "first_name",
            "last_name",
            "second_last_name",
            "full_name",
            "rut",
            "phone",
            "birth_date",
            "avatar",
            "address",
            "updated_at",
        ]
        read_only_fields = fields


class ProfileWriteSerializer(serializers.Serializer):
    """Write: valida los datos del perfil. La persistencia la delega el servicio."""

    first_name = serializers.CharField(
        max_length=100,
        required=True,
        error_messages={
            "max_length": _("First name cannot exceed 100 characters."),
            "blank": _("First name cannot be blank."),
        },
    )
    last_name = serializers.CharField(
        max_length=100,
        required=True,
        error_messages={
            "max_length": _("Last name cannot exceed 100 characters."),
            "blank": _("Last name cannot be blank."),
        },
    )
    second_last_name = serializers.CharField(
        max_length=100,
        required=True,
        error_messages={
            "max_length": _("Second last name cannot exceed 100 characters."),
        },
    )
    rut = serializers.CharField(
        max_length=12,
        required=True,
        error_messages={
            "max_length": _("RUT cannot exceed 12 characters."),
        },
    )
    phone = serializers.CharField(
        max_length=20,
        required=True,
        error_messages={
            "max_length": _("Phone number cannot exceed 20 characters."),
        },
    )
    birth_date = serializers.DateField(
        required=True,
        error_messages={
            "invalid": _("Enter a valid date in YYYY-MM-DD format."),
        },
    )
    avatar = serializers.ImageField(
        required=False,
        allow_null=True,
        error_messages={
            "invalid_image": _("Upload a valid image file."),
        },
    )
    address = serializers.CharField(
        max_length=255,
        required=True,
        error_messages={
            "max_length": _("Address cannot exceed 255 characters."),
        },
    )
