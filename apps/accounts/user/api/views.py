from datetime import timedelta

from django.db.models import Q
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError, AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from djoser.views import UserViewSet
from djoser.serializers import UserSerializer, UserCreatePasswordRetypeSerializer

from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema_view,
    extend_schema,
    OpenApiResponse,
)


from apps.accounts.user.api.docs import DocTags
from apps.common.api.serializers import (
    DetailResponseSerializer,
    ProblemDetailsSerializer,
)
from apps.accounts.user.api.serializers import (
    CustomTokenObtainPairSerializer,
    CustomUserSerializer,
    TokenValidateResponseSerializer,
    UserLoginSerializer,
    UserLoginResponseSerializer,
)

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter


User = get_user_model()


@extend_schema(
    tags=["Authentication"],
    summary="User Login",
    description="Authenticate user with email and password. Returns access token in response body and refresh token in HttpOnly cookie.",
    request=UserLoginSerializer,
    responses={
        200: OpenApiResponse(
            response=UserLoginResponseSerializer,
            description="Login successful. Access token returned in body, refresh token set in cookie.",
        ),
        400: OpenApiResponse(
            response=ProblemDetailsSerializer,
            description="Validation error (missing or invalid fields).",
        ),
        401: OpenApiResponse(
            response=ProblemDetailsSerializer,
            description="Authentication failed (invalid credentials or inactive account).",
        ),
    },
)
class UserLoginAPIView(APIView):
    """
    API endpoint for user login.
    Validates credentials and returns a JWT access token.
    Refresh token is set in a secure cookie.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request: Request) -> Response:
        login_serializer = UserLoginSerializer(
            data=request.data, context={"request": request}
        )

        login_serializer.is_valid(raise_exception=True)
        user = login_serializer.validated_data["user"]  # type: ignore

        # Generar tokens
        refresh = CustomTokenObtainPairSerializer.get_token(user)
        access_token = str(refresh.access_token)  # type: ignore

        response = Response(
            {"access": access_token},
            status=status.HTTP_200_OK,
        )

        # Configuración de Cookie
        # Intentamos obtener la duración desde settings, fallback a 7 días
        refresh_lifetime = getattr(settings, "SIMPLE_JWT", {}).get(
            "REFRESH_TOKEN_LIFETIME", timedelta(days=7)
        )
        # Si es timedelta, lo convertimos a segundos
        max_age = (
            int(refresh_lifetime.total_seconds())
            if isinstance(refresh_lifetime, timedelta)
            else 7 * 24 * 60 * 60
        )

        response.set_cookie(
            key="refresh_token",
            value=str(refresh),
            httponly=True,
            secure=not settings.DEBUG,  # Seguro en producción (HTTPS)
            samesite="Lax",  # Protección CSRF moderada
            max_age=max_age,
            path="/",
        )

        return response


@extend_schema(
    tags=["Authentication"],
    summary="Refresh Access Token",
    description="Obtain a new access token using the refresh token stored in HttpOnly cookie.",
    request=None,
    responses={
        200: OpenApiResponse(
            response=UserLoginResponseSerializer,
            description="New access token generated successfully.",
        ),
        400: OpenApiResponse(
            response=ProblemDetailsSerializer,
            description="Refresh token not found in cookies.",
        ),
        401: OpenApiResponse(
            response=ProblemDetailsSerializer,
            description="Invalid or expired refresh token.",
        ),
    },
)
class TokenRefreshView(APIView):
    """
    View to refresh the access token using the refresh token from the cookie.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request: Request) -> Response:
        """
        Obtain a new access token using the cookie's refresh token.
        """

        refresh_token = request.COOKIES.get("refresh_token")

        if not refresh_token:
            raise ValidationError({"error": [_("Refresh token not found in cookies.")]})

        try:
            refresh = RefreshToken(refresh_token)
            access_token = str(refresh.access_token)

            return Response({"access": access_token}, status=status.HTTP_200_OK)

        except TokenError:
            raise AuthenticationFailed(
                {"error": [_("Invalid or expired refresh token.")]}
            )
        except Exception:
            # En producción no deberíamos exponer el error raw al usuario,
            # pero lo mantenemos por ahora para debugging controlado o lo loggeamos.
            raise ValidationError({"error": [_("Unexpected refresh error.")]})


@extend_schema(
    tags=["Authentication"],
    summary="User Logout",
    description="Logout user by invalidating the refresh token and removing the cookie.",
    request=None,
    responses={
        200: OpenApiResponse(
            response=DetailResponseSerializer,
            description="Logout successful. Refresh token cookie removed.",
        ),
        400: OpenApiResponse(
            response=ProblemDetailsSerializer,
            description="Refresh token not found in cookies.",
        ),
    },
)
class UserLogoutView(APIView):
    """
    View to logout by removing the refresh token cookie.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request: Request) -> Response:
        refresh_token = request.COOKIES.get("refresh_token")

        if not refresh_token:
            # Si no hay cookie, asumimos que ya salió o nunca entró.
            # Retornamos 200 para ser idempotentes, o error si prefieres estricto.
            # Por consistencia con la implementación previa, retornamos error.
            raise ValidationError({"error": [_("Refresh token not found in cookies.")]})

        try:
            refresh = RefreshToken(refresh_token)
            refresh.blacklist()

            response = Response(
                {"detail": _("Logged out successfully.")},
                status=status.HTTP_200_OK,
            )

            response.delete_cookie(
                key="refresh_token",
                samesite="Lax",
                path="/",
            )

            return response

        except TokenError:
            # Si el token es inválido, igual queremos borrar la cookie
            response = Response(
                {"detail": _("Logged out successfully (token was invalid).")},
                status=status.HTTP_200_OK,
            )
            response.delete_cookie(key="refresh_token", samesite="Lax", path="/")
            return response

        except Exception:
            raise ValidationError({"error": [_("Unexpected logout error.")]})


@extend_schema(
    tags=["Authentication"],
    summary="Verify token",
    responses={
        status.HTTP_200_OK: OpenApiResponse(
            response=TokenValidateResponseSerializer, description="Token validate"
        ),
        status.HTTP_400_BAD_REQUEST: OpenApiResponse(
            response=ProblemDetailsSerializer,
            description="Validation error",
        ),
        status.HTTP_500_INTERNAL_SERVER_ERROR: OpenApiResponse(
            response=ProblemDetailsSerializer,
            description="Server error during login.",
        ),
    },
)
class VerifyToken(APIView):
    def get(self, request: Request) -> Response:
        return Response({"validate": True}, status=status.HTTP_200_OK)


_SEARCH_PARAM = OpenApiParameter(
    name="search",
    type=str,
    location=OpenApiParameter.QUERY,
    description=(
        "Búsqueda de texto libre. Aplica sobre **email**, **first_name**, "
        "**last_name** y **rut** del perfil asociado. "
        "Ejemplo: `search=Gonzalez`"
    ),
)

_ORDERING_PARAM = OpenApiParameter(
    name="ordering",
    type=str,
    location=OpenApiParameter.QUERY,
    description=(
        "Campo por el cual ordenar los resultados. "
        "Se debe usar el prefijo `-` para orden descendente. "
        "Valores permitidos: `email`,  `is_active`, "
        "`profile__first_name`, `profile__last_name` y `profile__rut`. "
        "Ejemplo: `ordering=profile__last_name`"
    ),
)

_USER_FILTER_PARAMS = [
    OpenApiParameter(
        "is_active",
        bool,
        OpenApiParameter.QUERY,
        description="Estado del usuario. `true` indica activos, `false` indica inactivos.",
    ),
]


@extend_schema_view(
    create=extend_schema(
        tags=[DocTags.TAG_USER],
        summary="Create a new user",
        description="Endpoint to create a new user.",
        request=UserCreatePasswordRetypeSerializer,
        responses={
            status.HTTP_201_CREATED: OpenApiResponse(
                response=UserSerializer,
                description="Account created successfully",
            ),
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                response=ProblemDetailsSerializer,
                description="Validation error",
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: OpenApiResponse(
                response=ProblemDetailsSerializer,
                description="Server error during login.",
            ),
        },
    ),
    list=extend_schema(
        tags=[DocTags.TAG_ADMIN_USER],
        summary="List users",
        description="Retrieve a paginated list of all users.",
        parameters=[_SEARCH_PARAM, _ORDERING_PARAM, *_USER_FILTER_PARAMS],
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                response=CustomUserSerializer(many=True),
                description="List of accounts retrieved successfully.",
            ),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(
                response=ProblemDetailsSerializer,
                description="Authentication credentials were not provided or are invalid.",
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: OpenApiResponse(
                response=ProblemDetailsSerializer,
                description="Server error during login.",
            ),
        },
    ),
    retrieve=extend_schema(
        tags=[DocTags.TAG_ADMIN_USER],
        summary="Retrieve user details",
        description="Fetch a specific user by ID.",
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                response=CustomUserSerializer,
                description="Account details",
            ),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(
                response=ProblemDetailsSerializer,
                description="Authentication credentials were not provided or are invalid.",
            ),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(
                response=ProblemDetailsSerializer,
                description="Account not found",
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: OpenApiResponse(
                response=ProblemDetailsSerializer,
                description="Server error during login.",
            ),
        },
    ),
    destroy=extend_schema(
        tags=[DocTags.TAG_ADMIN_USER],
        summary="Delete a user",
        description="Delete a specific user by ID.",
        responses={
            status.HTTP_204_NO_CONTENT: OpenApiResponse(
                description="User deleted successfully"
            ),
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                response=ProblemDetailsSerializer,
                description="Validation Error",
            ),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(
                response=ProblemDetailsSerializer,
                description="Authentication credentials were not provided or are invalid.",
            ),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(
                response=ProblemDetailsSerializer,
                description="Account not found",
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: OpenApiResponse(
                response=ProblemDetailsSerializer,
                description="Server error during login.",
            ),
        },
    ),
    activation=extend_schema(
        tags=[DocTags.TAG_USER_ACTIVATION],
        summary="Activate user",
        description=("Activate a user using the unique UID and token sent via email. "),
        responses={
            status.HTTP_204_NO_CONTENT: OpenApiResponse(
                description="Account successfully activated. No content returned."
            ),
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                response=ProblemDetailsSerializer,
                description="Validation Error",
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: OpenApiResponse(
                response=ProblemDetailsSerializer,
                description="Server error during login.",
            ),
        },
    ),
    resend_activation=extend_schema(
        tags=[DocTags.TAG_USER_ACTIVATION],
        summary="Resend activation email",
        description=(
            "Resend the activation email if the user has not been activated yet."
        ),
        responses={
            status.HTTP_204_NO_CONTENT: OpenApiResponse(
                description="Activation email resent successfully."
            ),
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                response=ProblemDetailsSerializer,
                description="Validation Error",
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: OpenApiResponse(
                response=ProblemDetailsSerializer,
                description="Server error during login.",
            ),
        },
    ),
    reset_password=extend_schema(
        tags=[DocTags.TAG_PASSWORD_RESET],
        summary="Request password reset",
        description=(
            "Send a password reset email containing a unique token to the user's email address."
        ),
        responses={
            status.HTTP_204_NO_CONTENT: OpenApiResponse(
                description="Password reset email sent successfully."
            ),
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                response=ProblemDetailsSerializer,
                description="Validation Error",
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: OpenApiResponse(
                response=ProblemDetailsSerializer,
                description="Server error during login.",
            ),
        },
    ),
    reset_password_confirm=extend_schema(
        tags=[DocTags.TAG_PASSWORD_RESET],
        summary="Confirm password reset",
        description=(
            "Confirm password reset by providing the UID, token, and new password values."
        ),
        responses={
            status.HTTP_204_NO_CONTENT: OpenApiResponse(
                description="Password reset successfully completed."
            ),
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                response=ProblemDetailsSerializer,
                description="Validation Error",
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: OpenApiResponse(
                response=ProblemDetailsSerializer,
                description="Server error during login.",
            ),
        },
    ),
    set_password=extend_schema(
        tags=[DocTags.TAG_PASSWORD_RESET],
        summary="Set a new password",
        description=(
            "Allow authenticated users to change their password by providing the current password, "
            "and the new password (with confirmation)."
        ),
        responses={
            status.HTTP_204_NO_CONTENT: OpenApiResponse(
                description="Password successfully updated."
            ),
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                response=ProblemDetailsSerializer,
                description="Validation Error",
            ),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(
                response=ProblemDetailsSerializer,
                description="Authentication credentials were not provided or are invalid.",
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: OpenApiResponse(
                response=ProblemDetailsSerializer,
                description="Server error during login.",
            ),
        },
    ),
)
class CustomUserViewSet(UserViewSet):
    """UserViewSet with extended documentation for OpenAPI/Swagger."""

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = [
        "email",
        "profile__first_name",
        "profile__last_name",
        "profile__rut",
    ]
    ordering_fields = [
        "email",
        "is_active",
        "profile__first_name",
        "profile__last_name",
        "profile__rut",
    ]
    ordering = ["-created_at"]
    filterset_fields = ["is_active"]

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.select_related("profile", "membership")

    @extend_schema(exclude=True)
    def set_username(self, request, *args, **kwargs):
        raise NotImplementedError("This endpoint is disabled.")

    @extend_schema(exclude=True)
    def reset_username(self, request, *args, **kwargs):
        raise NotImplementedError("This endpoint is disabled.")

    @extend_schema(exclude=True)
    def reset_username_confirm(self, request, *args, **kwargs):
        raise NotImplementedError("This endpoint is disabled.")

    @extend_schema(exclude=True)
    def update(self, request, *args, **kwargs):
        raise NotImplementedError("This endpoint is disabled.")

    @extend_schema(exclude=True)
    def partial_update(self, request, *args, **kwargs):
        raise NotImplementedError("This endpoint is disabled.")

    @extend_schema(
        tags=[DocTags.TAG_USER],
        methods=["GET"],
        summary="Retrieve current user",
        description=("Retrieve the information of the currently authenticated user"),
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description="Current user data retrieved successfully",
                response=CustomUserSerializer,
            ),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(
                description="Authentication credentials were not provided or are invalid.",
                response=ProblemDetailsSerializer,
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: OpenApiResponse(
                response=ProblemDetailsSerializer,
                description="Server error during login.",
            ),
        },
    )
    @extend_schema(
        tags=[DocTags.TAG_USER],
        exclude=True,
        methods=["PUT", "PATCH"],
        summary="Update current user",
        description="Update user data.",
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description="User data",
                response=UserSerializer,
            ),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(
                description="Authentication credentials were not provided or are invalid.",
                response=ProblemDetailsSerializer,
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: OpenApiResponse(
                description="Server error during login.",
                response=ProblemDetailsSerializer,
            ),
        },
    )
    @extend_schema(
        tags=[DocTags.TAG_USER],
        summary="Delete current user",
        description="Delete the current authenticated user. No request body required.",
        request=None,
        responses={
            status.HTTP_204_NO_CONTENT: OpenApiResponse(
                description="User deleted succesfully"
            ),
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                response=ProblemDetailsSerializer,
                description="Validation Error",
            ),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(
                response=ProblemDetailsSerializer,
                description="Authentication credentials were not provided or are invalid.",
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: OpenApiResponse(
                response=ProblemDetailsSerializer,
                description="Server error during login.",
            ),
        },
    )
    @action(["get", "put", "patch", "delete"], detail=False)
    def me(self, request, *args, **kwargs):
        self.get_object = self.get_instance  # type: ignore

        if request.method == "GET":
            return self.retrieve(request, *args, **kwargs)
        elif request.method == "PUT":
            # return self.update(request, *args, **kwargs)
            raise NotImplementedError("This endpoint is disabled.")
        elif request.method == "PATCH":
            # return self.partial_update(request, *args, **kwargs)
            raise NotImplementedError("This endpoint is disabled.")
        elif request.method == "DELETE":
            return self.destroy(request, *args, **kwargs)
