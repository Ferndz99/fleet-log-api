from apps.common.domain.exceptions import DomainError


class InvitationExpired(DomainError):
    status_code = 409
    title = "Invitation expired"
    default_detail = "Invitation '{invitation}' expired."
    code = "invitation_expired"