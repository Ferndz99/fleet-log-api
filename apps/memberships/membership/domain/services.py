from apps.accounts.user.domain.services import UserRegistrationService
from apps.memberships.choices import Role
from apps.memberships.membership.domain.exceptions import (
    MembershipAlreadyActive,
    MembershipAlreadyInactive,
    OwnerCannotDeactivate,
)
from apps.memberships.membership.domain.models import Membership
from typing import Optional
from django.db import transaction


class MembershipService:
    @staticmethod
    def activate(*, membership: Membership, performed_by):

        if membership.is_active:
            raise MembershipAlreadyActive(membership=membership.user)

        membership.is_active = True
        membership.save(update_fields=["is_active"])
        UserRegistrationService.activate(user=membership.user)

    @staticmethod
    @transaction.atomic
    def create(
        *,
        user,
        is_active: Optional[bool] = True,
    ) -> Membership:

        return Membership.objects.create(
            user=user,
            is_active=is_active,
        )

    @staticmethod
    def deactivate(*, membership: Membership, performed_by):

        if not membership.is_active:
            raise MembershipAlreadyInactive(membership=membership.user)

        membership.is_active = False
        membership.save(update_fields=["is_active"])
        UserRegistrationService.deacticate(user=membership.user)
