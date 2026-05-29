from rest_framework.permissions import BasePermission

from apps.memberships.choices import Role
from apps.memberships.membership.domain.models import Membership


class BaseCompanyRolePermission(BasePermission):
    allowed_roles: list[str] = []

    def has_permission(self, request, view):  # type: ignore

        return Membership.objects.filter(
            user=request.user,
            role__in=self.allowed_roles,
            is_active=True,
        ).exists()


class HasCompanyOwnerPermissions(BaseCompanyRolePermission):
    allowed_roles = [Role.OWNER]


class HasCompanyOwnerOrAdminPermissions(BaseCompanyRolePermission):
    allowed_roles = [Role.OWNER, Role.ADMIN]


class HasCompanyReadPermissions(BaseCompanyRolePermission):
    allowed_roles = [
        Role.OWNER,
        Role.ADMIN,
        Role.SELLER,
        Role.VIEWER,
    ]
