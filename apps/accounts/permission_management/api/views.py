from django.contrib.auth.models import Group, Permission
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model


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


class GroupViewSet(ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer

    serializer_class_by_action = {
        "add_users": AddUserGroupSerializer,
        "remove_users": RemoveUserGroupSerializer,
        "add_permissions": AddPermissionGroupSerializer,
        "remove_permissions": RemovePermissionGroupSerializer,
        "retrieve": GroupDetailSerializer
    }

    def get_serializer_class(self):
        return self.serializer_class_by_action.get(self.action, self.serializer_class)

    @action(detail=True, methods=["get"])
    def users(self, request, pk=None):
        group = self.get_object()
        users = group.user_set.all()
        return Response(CustomUserSerializer(users, many=True).data)

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
