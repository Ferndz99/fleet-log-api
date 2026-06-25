from django.contrib.auth.models import Permission, Group
from rest_framework import serializers
from django.contrib.auth import get_user_model

from apps.accounts.user.api.serializers import CustomUserSerializer

User = get_user_model()


class PermissionSerializer(serializers.ModelSerializer):
    app_label = serializers.CharField(source="content_type.app_label", read_only=True)

    model = serializers.CharField(source="content_type.model", read_only=True)

    class Meta:
        model = Permission
        fields = [
            "id",
            "name",
            "codename",
            "app_label",
            "model",
        ]


class GroupSerializer(serializers.ModelSerializer):
    # permissions = serializers.SlugRelatedField(
    #     many=True, read_only=True, slug_field="name"
    # )

    # permissions = PermissionSerializer(many=True, read_only=True)

    class Meta:
        model = Group
        fields = [
            "id",
            "name",
        ]


class GroupDetailSerializer(serializers.ModelSerializer):
    # permissions = serializers.SlugRelatedField(
    #     many=True, read_only=True, slug_field="name"
    # )

    permissions = PermissionSerializer(many=True, read_only=True)
    users = CustomUserSerializer(many=True, read_only=True, source="user_set")

    class Meta:
        model = Group
        fields = ["id", "name", "permissions", "users"]


class AddUserGroupSerializer(serializers.Serializer):
    user_ids = serializers.ListField(child=serializers.IntegerField())


class RemoveUserGroupSerializer(serializers.Serializer):
    user_ids = serializers.ListField(child=serializers.IntegerField())


class AddPermissionGroupSerializer(serializers.Serializer):
    permission_ids = serializers.ListField(child=serializers.IntegerField())


class RemovePermissionGroupSerializer(serializers.Serializer):
    permission_ids = serializers.ListField(child=serializers.IntegerField())
