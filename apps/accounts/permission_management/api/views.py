from django.contrib.auth.models import Group, Permission
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from drf_spectacular.types import OpenApiTypes

from apps.accounts.permission_management.api.serializers import (
    AddPermissionGroupSerializer,
    AddUserGroupSerializer,
    GroupDetailSerializer,
    GroupSerializer,
    PermissionSerializer,
    RemovePermissionGroupSerializer,
    RemoveUserGroupSerializer,
)
from apps.accounts.user.api.serializers import CustomUserSerializer


User = get_user_model()


class PermissionViewSet(ReadOnlyModelViewSet):
    queryset = Permission.objects.select_related("content_type").order_by(
        "content_type__app_label"
    )

    serializer_class = PermissionSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name", "model"]
    ordering_fields = ["model"]
    pagination_class = None


class GroupViewSet(ModelViewSet):
    queryset = Group.objects.annotate(
        permission_count=Count("permissions", distinct=True),
        users_count=Count("user", distinct=True),
    )
    serializer_class = GroupSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name", "permission_count", "users_count"]
    ordering = ["name"]
    # filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    # search_fields = [
    #     ""
    # ]

    serializer_class_by_action = {
        "add_users": AddUserGroupSerializer,
        "remove_users": RemoveUserGroupSerializer,
        "add_permissions": AddPermissionGroupSerializer,
        "remove_permissions": RemovePermissionGroupSerializer,
        "retrieve": GroupDetailSerializer,
        "set_users": AddUserGroupSerializer,
        "set_permissions": AddPermissionGroupSerializer,
    }

    def get_serializer_class(self):
        return self.serializer_class_by_action.get(self.action, self.serializer_class)

    # @action(detail=True, methods=["get"])
    # def users(self, request, pk=None):
    #     group = self.get_object()
    #     users = group.user_set.all()
    #     return Response(CustomUserSerializer(users, many=True).data)

    @action(detail=True, methods=["post"])
    def add_users(self, request, pk=None):
        group = self.get_object()
        # user_ids = request.data.get("user_ids", [])
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        group.user_set.add(
            *User.objects.filter(id__in=serializer.validated_data["user_ids"])
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def remove_users(self, request, pk=None):
        group = self.get_object()
        # user_ids = request.data.get("user_ids", [])
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group.user_set.remove(
            *User.objects.filter(id__in=serializer.validated_data["user_ids"])
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def add_permissions(self, request, pk=None):
        group = self.get_object()
        # perm_ids = request.data.get("permission_ids", [])
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group.permissions.add(
            *Permission.objects.filter(
                id__in=serializer.validated_data["permission_ids"]
            )
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def remove_permissions(self, request, pk=None):
        group = self.get_object()
        # perm_ids = request.data.get("permission_ids", [])
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group.permissions.remove(
            *Permission.objects.filter(
                id__in=serializer.validated_data["permission_ids"]
            )
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


    @extend_schema(
        request=AddUserGroupSerializer,
        responses={
            204: OpenApiResponse(description="", response=None)
        }
    )
    @action(detail=True, methods=["post"])
    def set_users(self, request, pk=None):
        group = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        users = User.objects.filter(id__in=serializer.validated_data["user_ids"])
        group.user_set.set(users)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def set_permissions(self, request, pk=None):
        group = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        permissions = Permission.objects.filter(
            id__in=serializer.validated_data["permission_ids"]
        )
        group.permissions.set(permissions)
        return Response(status=status.HTTP_204_NO_CONTENT)
