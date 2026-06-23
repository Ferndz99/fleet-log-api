from datetime import timedelta
import hashlib
import secrets
from django.db import transaction

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from django.utils import timezone

from apps.accounts.user.domain.services import UserRegistrationService
from apps.memberships.choices import Status
from apps.memberships.invitation.domain.exceptions import (
    InvitationAlreadyUsed,
    InvitationExpired,
    InvitationNotFound,
)
from apps.memberships.invitation.domain.models import Invitation
from apps.memberships.membership.domain.models import Membership


class InvitationService:
    INVITATION_EXPIRATION_HOURS = 48

    @staticmethod
    def create(*, email: str, invited_by, is_staff: bool = False) -> Invitation:

        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        invitation = Invitation.objects.create(
            email=email,
            invited_by=invited_by,
            token_hash=token_hash,
            is_staff=is_staff,
            expires_at=timezone.now()
            + timedelta(hours=InvitationService.INVITATION_EXPIRATION_HOURS),
        )

        invitation.raw_token = raw_token

        return invitation

    @staticmethod
    def send_invitation_email_service(*, invitation: Invitation) -> None:
        print("aqui")
        invite_url = (
            f"{settings.FRONTEND_URL}/accept-invitation?token={invitation.raw_token}"
        )

        subject = "Invitación a unirte a una empresa"
        from_email = settings.DEFAULT_FROM_EMAIL
        to = [invitation.email]

        context = {
            "invite_url": invite_url,
        }

        html_content = render_to_string("emails/invitation.html", context)

        msg = EmailMultiAlternatives(
            subject=subject,
            body="Has sido invitado a una empresa",
            from_email=from_email,
            to=to,
        )

        msg.mixed_subtype = "related"
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        print("ejecutado")

    @staticmethod
    def invite_user(*, email: str, invited_by, is_staff: bool = False):
        invitation = InvitationService.create(
            email=email, invited_by=invited_by, is_staff=is_staff
        )

        InvitationService.send_invitation_email_service(invitation=invitation)
        return invitation

    @staticmethod
    def validate_token(*, token: str) -> Invitation:
        """
        Valida que un token de invitación exista y siga siendo utilizable.
        Si encuentra que ya expiró, actualiza su status a EXPIRED en este
        mismo momento (expiración perezosa) para mantener la BD consistente
        sin depender de un job periódico.
        """
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        with transaction.atomic():
            try:
                invitation = Invitation.objects.select_for_update().get(
                    token_hash=token_hash
                )
            except Invitation.DoesNotExist:
                raise InvitationNotFound()

            if invitation.status == Status.PENDING and invitation.is_expired():
                invitation.status = Status.EXPIRED
                invitation.save(update_fields=["status"])

        if invitation.status == Status.EXPIRED:
            raise InvitationExpired(invitation=invitation)

        if invitation.status == Status.ACCEPTED:
            raise InvitationAlreadyUsed(invitation=invitation)

        return invitation

    @staticmethod
    @transaction.atomic
    def accept_invitation(*, token: str, password: str):

        token_hash = hashlib.sha256(token.encode()).hexdigest()

        try:
            invitation = Invitation.objects.select_for_update().get(
                token_hash=token_hash
            )
        except Invitation.DoesNotExist:
            raise InvitationNotFound()

        # Expiración perezosa

        if invitation.status == Status.PENDING and invitation.is_expired():
            invitation.status = Status.EXPIRED
            invitation.save(update_fields=["status"])

        if invitation.status == Status.EXPIRED:
            raise InvitationExpired(invitation=invitation)

        if invitation.status == Status.ACCEPTED:
            raise InvitationAlreadyUsed(invitation=invitation)

        # if (
        #     invitation.status == Status.PENDING
        #     and invitation.expires_at < timezone.now()
        # ):
        #     invitation.status = Status.EXPIRED
        #     invitation.save(update_fields=["status"])

        # if invitation.status == Status.EXPIRED:
        #     raise InvitationExpired(invitation=invitation)

        # if invitation.status != Status.PENDING:
        #     raise InvitationAlreadyUsed(invitation=invitation)

        # invitation = Invitation.objects.select_for_update().get(
        #     token_hash=token_hash, status=Status.PENDING
        # )

        # if invitation.expires_at < timezone.now():
        #     raise InvitationExpired(invitation=invitation.pk)

        user = UserRegistrationService.get_or_create_user(
            email=invitation.email,
            password=password,
            is_staff=invitation.is_staff,
        )

        Membership.objects.create(
            user=user,
            invited_at=invitation.created_at,
        )

        invitation.status = Status.ACCEPTED
        invitation.save(update_fields=["status"])

        (
            Invitation.objects.select_for_update()
            .filter(email=invitation.email, status=Status.PENDING)
            .exclude(pk=invitation.pk)
            .update(status=Status.EXPIRED)
        )

        return user
