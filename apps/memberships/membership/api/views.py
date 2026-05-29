from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.filters import SearchFilter, OrderingFilter

from django_filters.rest_framework import DjangoFilterBackend

from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from apps.common.api.serializers import ProblemDetailsSerializer
from apps.memberships.membership.api.filters import MembershipFilter
from apps.memberships.membership.application.permissions import HasCompanyOwnerOrAdminPermissions
from apps.memberships.membership.api.serializers import MembershipReadSerializer
from apps.memberships.membership.domain.models import Membership

from apps.memberships.membership.domain.services import MembershipService




@extend_schema_view(
    list=extend_schema(
        summary="List company memberships",
        description="Returns all memberships associated with the authenticated user's company.",
        responses={
            200: MembershipReadSerializer(many=True),
            500: ProblemDetailsSerializer,
        },
        tags=["Memberships"],
        parameters=[
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Search by user email",
            ),
            OpenApiParameter(
                name="ordering",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Order by: joined_at, invited_at, role. Use '-' prefix for descending.",
            ),
            OpenApiParameter(
                name="is_active",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description="Filter by active status.",
            ),
            OpenApiParameter(
                name="invited",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description=(
                    "Filter invited memberships.\n"
                    "true  → joined_at is null\n"
                    "false → joined_at is not null"
                ),
            ),
            OpenApiParameter(
                name="joined_after",
                type=OpenApiTypes.DATETIME,
                location=OpenApiParameter.QUERY,
                description="Filter memberships joined after this datetime (>= joined_at).",
            ),
            OpenApiParameter(
                name="joined_before",
                type=OpenApiTypes.DATETIME,
                location=OpenApiParameter.QUERY,
                description="Filter memberships joined before this datetime (<= joined_at).",
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Retrieve membership",
        description="Retrieve details of a specific membership within the company.",
        responses={
            200: MembershipReadSerializer,
            404: ProblemDetailsSerializer,
            500: ProblemDetailsSerializer,
        },
        tags=["Memberships"],
    ),
)
class MembershipViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):
    serializer_class = MembershipReadSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    ]
    search_fields = ["user__email"]
    ordering_fields = ["joined_at", "invited_at"]
    filterset_class = MembershipFilter

    def get_queryset(self):  # type: ignore
        return Membership.objects.all()

    @extend_schema(
        methods=["POST"],
        summary="deactivate membership",
        request=None,
        responses={200: MembershipReadSerializer, 400: ProblemDetailsSerializer},
        tags=["Memberships"],
    )
    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):

        membership = self.get_object()

        MembershipService.deactivate(
            membership=membership, performed_by=request.user
        )

        membership.refresh_from_db()

        serializer = self.get_serializer(membership)

        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        methods=["POST"],
        summary="activate membership",
        request=None,
        responses={200: MembershipReadSerializer, 400: ProblemDetailsSerializer},
        tags=["Memberships"],
    )
    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):

        membership = self.get_object()

        MembershipService.activate(
            membership=membership, performed_by=request.user
        )

        membership.refresh_from_db()

        serializer = self.get_serializer(membership)

        return Response(serializer.data, status=status.HTTP_200_OK)
