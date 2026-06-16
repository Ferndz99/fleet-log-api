from typing import Any, Dict

from django.contrib.auth import authenticate, get_user_model
from django.utils.translation import gettext_lazy as _


from rest_framework import serializers
from rest_framework.exceptions import ValidationError, AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from djoser.serializers import UserSerializer


User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Customizes the JWT token by adding extra user information (role, staff status, email).
    """

    @classmethod
    def get_token(cls, user: User) -> Dict[str, Any]:  # type: ignore
        token = super().get_token(user)
        token["email"] = user.email  # type: ignore
        token["is_staff"] = user.is_staff  # type: ignore

        return token  # type: ignore


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(
        required=True,
        error_messages={
            "required": _("Email is required."),
            "blank": _("This field cannot be blank."),
            "invalid": _("Please enter a valid email address."),
        },
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        error_messages={
            "required": _("Password is required."),
            "blank": _("This field cannot be blank."),
        },
    )

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates the email and password, authenticating the user.
        """
        email = attrs.get("email")
        password = attrs.get("password")

        user = authenticate(
            request=self.context.get("request"), email=email, password=password
        )

        if user is None:
            raise AuthenticationFailed(
                _("Account not found with the given credentials.")
            )

        if not user.is_active:
            raise ValidationError(
                _("This account is deactivated. Please contact support.")
            )

        attrs["user"] = user
        return attrs


class UserLoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField()


class TokenValidateResponseSerializer(serializers.Serializer):
    validate = serializers.CharField()  # type: ignore


class CustomUserSerializer(UserSerializer):
    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ("is_staff",)
