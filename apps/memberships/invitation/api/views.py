from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import ListModelMixin, CreateModelMixin
from rest_framework import serializers

from django_filters.rest_framework import DjangoFilterBackend

from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
    OpenApiResponse,
    inline_serializer,
)
from drf_spectacular.types import OpenApiTypes

from apps.accounts.profile.domain.services import ProfileService
from apps.common.api.serializers import ProblemDetailsSerializer
from apps.memberships.invitation.domain.models import Invitation
from apps.memberships.invitation.application.permissions import (
    HasCompanyOwnerOrAdminPermissions,
)

from apps.memberships.invitation.api.serializers import (
    InvitationCreateSerializer,
    InvitationAcceptSerializer,
    InvitationReadSerializer,
)
from apps.memberships.invitation.domain.services import (
    InvitationService,
)


@extend_schema_view(
    list=extend_schema(
        summary="List company invitations",
        description="Returns invitations belonging to the authenticated user's company.",
        parameters=[
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Search invitations by email.",
            ),
            OpenApiParameter(
                name="ordering",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Order by created_at. Use '-' prefix for descending.",
                enum=["created_at", "-created_at"],
            ),
        ],
        responses={
            200: InvitationReadSerializer(many=True),
            500: ProblemDetailsSerializer,
        },
        tags=["Invitations"],
    ),
    create=extend_schema(
        summary="Create invitation",
        description="Invite a user to the company.",
        request=InvitationCreateSerializer,
        responses={
            201: InvitationReadSerializer,
            400: ProblemDetailsSerializer,
            500: ProblemDetailsSerializer,
        },
        tags=["Invitations"],
    ),
)
class InvitationViewSet(GenericViewSet, ListModelMixin, CreateModelMixin):
    queryset = Invitation.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["email"]
    ordering_fields = ["created_at"]
    serializer_class = InvitationReadSerializer
    permission_classes = []

    serializer_class_by_action = {
        "create": InvitationCreateSerializer,
        "accept": InvitationAcceptSerializer,
    }

    permission_classes_by_action = {"create": [IsAuthenticated, IsAdminUser]}

    def get_permissions(self):
        permission_classes = self.permission_classes_by_action.get(
            self.action, self.permission_classes
        )
        return [permission() for permission in permission_classes]

    def get_queryset(self):  # type: ignore
        return Invitation.objects.all()

    def get_serializer_class(self):
        return self.serializer_class_by_action.get(self.action, self.serializer_class)

    def perform_create(self, serializer):

        InvitationService.invite_user(
            email=serializer.validated_data["email"],
            invited_by=self.request.user,
        )

    @extend_schema(
        summary="Accept invitation",
        description=(
            "Accept an invitation using a token and set the account password. "
            "This endpoint does not require authentication."
        ),
        request=InvitationAcceptSerializer,
        responses={
            200: inline_serializer(
                name="InvitationAcceptedResponse",
                fields={"detail": serializers.CharField()},
            ),
            400: ProblemDetailsSerializer,
        },
        tags=["Invitations"],
    )
    @action(
        detail=False, methods=["post"], authentication_classes=[], permission_classes=[]
    )
    def accept(self, request):

        serializer = InvitationAcceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile_data = serializer.validated_data.pop("profile", {})

        user = InvitationService.accept_invitation(
            token=serializer.validated_data["token"],  # type: ignore
            password=serializer.validated_data["password"],  # type: ignore
        )

        if profile_data:
            ProfileService.create_profile(user, **profile_data)

        return Response(
            {"detail": "Invitation accepted"},
            status=status.HTTP_200_OK,
        )
