from rest_framework import serializers

from apps.memberships.choices import Role
from apps.memberships.invitation.domain.models import Invitation


class InvitationCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()


class InvitationAcceptSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(min_length=8, write_only=True)


class InvitationReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invitation
        fields = "__all__"
