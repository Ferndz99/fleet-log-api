from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class ErrorDetailSerializer(serializers.Serializer):
    """
    Serializer for individual error details.
    """

    field = serializers.CharField(
        help_text=_("Name of the field that produced the error")
    )
    message = serializers.CharField(help_text=_("Corresponding error message"))


class ProblemDetailsSerializer(serializers.Serializer):
    """
    Standard structure for error responses (RFC 7807).
    """

    type = serializers.URLField(
        required=False,
        allow_null=True,
        help_text=_("URL with information about the HTTP status code"),
    )
    status = serializers.IntegerField(required=True, help_text=_("HTTP status code"))
    title = serializers.CharField(
        required=True, help_text=_("Summary title of the error")
    )
    code = serializers.CharField(
        required=False,
        help_text=_(
            "Machine-readable error code identifier (e.g. 'validation_error', 'not_found')"
        ),
    )
    detail = serializers.CharField(
        required=True, help_text=_("Detailed description of the error")
    )
    instance = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text=_("Path or endpoint where the error occurred"),
    )
    _errors = ErrorDetailSerializer(
        many=True,
        required=False,
        help_text=_("List of validation errors per field"),
    )


class ErrorResponseSerializer(serializers.Serializer):
    """
    Standard error response structure.
    """

    error = serializers.ListField(
        child=serializers.CharField(), help_text=_("List of error messages")
    )


class DetailResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
