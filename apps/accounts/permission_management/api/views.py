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

from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)

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


_GROUP_SEARCH_PARAM = OpenApiParameter(
    name="search",
    type=str,
    location=OpenApiParameter.QUERY,
    description="Búsqueda de texto libre sobre **name**. Ejemplo: `search=Supervisor`",
)

_GROUP_ORDERING_PARAM = OpenApiParameter(
    name="ordering",
    type=str,
    location=OpenApiParameter.QUERY,
    description=(
        "Campo por el que ordenar los resultados. "
        "Prefija con `-` para orden descendente. "
        "Valores permitidos: `name`, `permission_count`, `users_count`. "
        "Ejemplo: `ordering=-users_count`"
    ),
)

_PERMISSION_SEARCH_PARAM = OpenApiParameter(
    name="search",
    type=str,
    location=OpenApiParameter.QUERY,
    description=(
        "Búsqueda de texto libre. Aplica sobre **name** y **model**. "
        "Ejemplo: `search=vehicle`"
    ),
)

_PERMISSION_ORDERING_PARAM = OpenApiParameter(
    name="ordering",
    type=str,
    location=OpenApiParameter.QUERY,
    description=(
        "Campo por el que ordenar los resultados. "
        "Valores permitidos: `model`. "
        "Ejemplo: `ordering=model`"
    ),
)


@extend_schema_view(
    list=extend_schema(
        tags=["Permissions"],
        summary="List permissions",
        description=(
            "Returns all permissions registered in the system. "
            "Supports **free-text search** (`search`) and **ordering** (`ordering`)."
        ),
        parameters=[_PERMISSION_SEARCH_PARAM, _PERMISSION_ORDERING_PARAM],
        responses=PermissionSerializer(many=True),
    ),
    retrieve=extend_schema(
        tags=["Permissions"],
        summary="Retrieve permission",
        description="Retrieve a single permission by its id.",
        responses=PermissionSerializer,
    ),
)
class PermissionViewSet(ReadOnlyModelViewSet):
    queryset = Permission.objects.select_related("content_type").order_by(
        "content_type__app_label"
    )

    serializer_class = PermissionSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name", "model"]
    ordering_fields = ["model"]
    pagination_class = None


@extend_schema_view(
    list=extend_schema(
        tags=["Groups"],
        summary="List groups",
        description=(
            "Returns a list of groups including their permission and user counts. "
            "Supports **free-text search** (`search`) and **ordering** (`ordering`)."
        ),
        parameters=[_GROUP_SEARCH_PARAM, _GROUP_ORDERING_PARAM],
        responses=GroupSerializer(many=True),
    ),
    retrieve=extend_schema(
        tags=["Groups"],
        summary="Retrieve group",
        description="Retrieve the full representation of a group including its nested permissions.",
        responses=GroupDetailSerializer,
    ),
    create=extend_schema(
        tags=["Groups"],
        summary="Create group",
        description="Create a new group (role).",
        request=GroupSerializer,
        responses={
            201: GroupDetailSerializer,
            400: OpenApiResponse(description="Validation error"),
        },
    ),
    update=extend_schema(
        tags=["Groups"],
        summary="Update group",
        description=(
            "Replace all fields of an existing group. Unlike `partial_update`, "
            "all required fields must be provided."
        ),
        request=GroupSerializer,
        responses={
            200: GroupDetailSerializer,
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="Group not found"),
        },
    ),
    partial_update=extend_schema(
        tags=["Groups"],
        summary="Partially update group",
        description="Update one or more fields of an existing group.",
        request=GroupSerializer,
        responses={
            200: GroupDetailSerializer,
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="Group not found"),
        },
    ),
    destroy=extend_schema(
        tags=["Groups"],
        summary="Delete group",
        description="Permanently delete a group. Users keep their other groups/permissions.",
        responses={
            204: OpenApiResponse(description="Group deleted successfully"),
            404: OpenApiResponse(description="Group not found"),
        },
    ),
    add_users=extend_schema(
        tags=["Groups"],
        summary="Add users to group",
        description="Incrementally adds the given users to the group, keeping existing members.",
        request=AddUserGroupSerializer,
        responses={204: OpenApiResponse(description="")},
    ),
    remove_users=extend_schema(
        tags=["Groups"],
        summary="Remove users from group",
        description="Incrementally removes the given users from the group.",
        request=RemoveUserGroupSerializer,
        responses={204: OpenApiResponse(description="")},
    ),
    add_permissions=extend_schema(
        tags=["Groups"],
        summary="Add permissions to group",
        description="Incrementally adds the given permissions to the group, keeping existing ones.",
        request=AddPermissionGroupSerializer,
        responses={204: OpenApiResponse(description="")},
    ),
    remove_permissions=extend_schema(
        tags=["Groups"],
        summary="Remove permissions from group",
        description="Incrementally removes the given permissions from the group.",
        request=RemovePermissionGroupSerializer,
        responses={204: OpenApiResponse(description="")},
    ),
    set_users=extend_schema(
        tags=["Groups"],
        summary="Set group users",
        description=(
            "Replaces the **full list** of users belonging to this group. "
            "Equivalent to a `PUT` over the user_ids M2M relation: any user not "
            "included in `user_ids` is removed from the group."
        ),
        request=AddUserGroupSerializer,
        responses={
            204: OpenApiResponse(description=""),
            400: OpenApiResponse(description="One or more user_ids do not exist"),
        },
    ),
    set_permissions=extend_schema(
        tags=["Groups"],
        summary="Set group permissions",
        description=(
            "Replaces the **full list** of permissions belonging to this group. "
            "Equivalent to a `PUT` over the permission_ids M2M relation: any "
            "permission not included in `permission_ids` is removed from the group."
        ),
        request=AddPermissionGroupSerializer,
        responses={
            204: OpenApiResponse(description=""),
            400: OpenApiResponse(description="One or more permission_ids do not exist"),
        },
    ),
)
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

    # @extend_schema(
    #     request=AddUserGroupSerializer,
    #     responses={204: OpenApiResponse(description="", response=None)},
    # )
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
