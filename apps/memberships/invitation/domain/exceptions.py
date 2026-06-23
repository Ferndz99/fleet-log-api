from apps.common.domain.exceptions import DomainError


class InvitationExpired(DomainError):
    status_code = 409
    title = "Invitation expired"
    default_detail = "Invitation '{invitation}' expired."
    code = "invitation_expired"

class InvitationNotFound(DomainError):
    status_code = 404
    title = "Invitation not found"
    default_detail = "Invitation does not exist"
    code = "invitation_not_found"


class InvitationAlreadyUsed(DomainError):
    status_code = 409
    title = "Invitiation already used"
    default_detail = "Invitation already used"
    code = "invitation_already_used"