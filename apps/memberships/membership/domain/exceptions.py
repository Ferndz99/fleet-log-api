from apps.common.domain.exceptions import DomainError


class MembershipAlreadyActive(DomainError):
    status_code = 409
    title = "Membership Already Active"
    default_detail = "Membership '{membership}' already exists."
    code = "membership_already_exists"


class MembershipAlreadyInactive(DomainError):
    status_code = 409
    title = "Membership Already Inactive"
    default_detail = "Membership '{membership}' already inactive."
    code = "membership_inactive"


class OwnerCannotDeactivate(DomainError):
    status_code = 409
    title = "Cannot deactivate owner"
    default_detail = "'{role}' cannot deactivate"
    code = "owner_restriction"