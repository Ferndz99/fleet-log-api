from rest_framework import serializers

from apps.accounts.profile.api.serializers import ProfileWriteSerializer
from apps.memberships.choices import Role
from apps.memberships.invitation.domain.models import Invitation


class InvitationCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    is_staff = serializers.BooleanField(default=False)


class InvitationAcceptSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(min_length=8, write_only=True)
    profile = ProfileWriteSerializer()


class InvitationReadSerializer(serializers.ModelSerializer):
    invited_by_email = serializers.SerializerMethodField()

    class Meta:
        model = Invitation
        fields = "__all__"

    def get_invited_by_email(self, obj):
        return obj.invited_by.email


class InvitationValidateResponseSerializer(serializers.Serializer):
    email = serializers.EmailField()
    is_staff = serializers.BooleanField()
    expires_at = serializers.DateTimeField()
