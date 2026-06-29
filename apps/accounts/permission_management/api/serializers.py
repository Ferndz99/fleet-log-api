from django.contrib.auth.models import Permission, Group
from rest_framework import serializers
from django.contrib.auth import get_user_model

from apps.accounts.user.api.serializers import CustomUserSerializer

from django.utils.translation import gettext_lazy as _

ACTION_LABELS = {
    "add": _("Add %(model)s"),
    "change": _("Change %(model)s"),
    "delete": _("Delete %(model)s"),
    "view": _("View %(model)s"),
}

CUSTOM_PERMISSION_LABELS = {
    "search_vehicle_by_patent": _("Can search vehicle by patent"),
}

User = get_user_model()


class PermissionSerializer(serializers.ModelSerializer):
    app_label = serializers.CharField(source="content_type.app_label", read_only=True)

    model = serializers.CharField(source="content_type.model", read_only=True)
    name = serializers.SerializerMethodField()

    class Meta:
        model = Permission
        fields = [
            "id",
            "name",
            "codename",
            "app_label",
            "model",
        ]

    def get_name(self, obj):
        codename = obj.codename

        # Permisos personalizados (ej: search_vehicle_by_patent)
        if codename in CUSTOM_PERMISSION_LABELS:
            return str(CUSTOM_PERMISSION_LABELS[codename])

        # Permisos CRUD estándar: add_<model>, change_<model>, delete_<model>, view_<model>
        action, _sep, _model_attr = codename.partition("_")
        model_class = obj.content_type.model_class()

        if action in ACTION_LABELS and model_class:
            model_verbose = model_class._meta.verbose_name
            return ACTION_LABELS[action] % {"model": model_verbose}

        # Fallback: lo que haya en la DB, por si no matchea ningún patrón
        return obj.name


class GroupSerializer(serializers.ModelSerializer):
    # permissions = serializers.SlugRelatedField(
    #     many=True, read_only=True, slug_field="name"
    # )

    # permissions = PermissionSerializer(many=True, read_only=True)

    permission_count = serializers.IntegerField(read_only=True)
    users_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Group
        fields = [
            "id",
            "name",
            "permission_count",
            "users_count",
        ]


class GroupDetailSerializer(serializers.ModelSerializer):
    # permissions = serializers.SlugRelatedField(
    #     many=True, read_only=True, slug_field="name"
    # )

    permissions = PermissionSerializer(many=True, read_only=True)
    users = CustomUserSerializer(many=True, read_only=True, source="user_set")
    permissions_ids = serializers.PrimaryKeyRelatedField(
        many=True, read_only=True, source="permissions"
    )
    users_ids = serializers.PrimaryKeyRelatedField(
        many=True, read_only=True, source="user_set"
    )

    class Meta:
        model = Group
        fields = [
            "id",
            "name",
            "permissions_ids",
            "users_ids",
            "permissions",
            "users",
        ]


class AddUserGroupSerializer(serializers.Serializer):
    user_ids = serializers.ListField(child=serializers.IntegerField())


class RemoveUserGroupSerializer(serializers.Serializer):
    user_ids = serializers.ListField(child=serializers.IntegerField())


class AddPermissionGroupSerializer(serializers.Serializer):
    permission_ids = serializers.ListField(child=serializers.IntegerField())


class RemovePermissionGroupSerializer(serializers.Serializer):
    permission_ids = serializers.ListField(child=serializers.IntegerField())
