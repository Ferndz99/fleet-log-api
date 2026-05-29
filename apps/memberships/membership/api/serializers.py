from rest_framework import serializers

from apps.memberships.membership.domain.models import Membership


class MembershipReadSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Membership
        fields = "__all__"
