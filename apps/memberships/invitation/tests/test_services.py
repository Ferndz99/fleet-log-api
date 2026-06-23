import pytest

from django.contrib.auth import get_user_model
from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone

from apps.memberships.choices import Status
from apps.memberships.invitation.domain.exceptions import (
    InvitationAlreadyUsed,
    InvitationExpired,
    InvitationNotFound,
)
from apps.memberships.invitation.domain.models import Invitation
from apps.memberships.invitation.domain.services import InvitationService
from apps.memberships.membership.domain.models import Membership


User = get_user_model()


@pytest.fixture
def admin_user(db):
    """Usuario que crea/envía la invitación (invited_by)."""
    return User.objects.create_user(
        email="admin@example.com",
        password="admin-password-123",
        is_staff=True,
    )


@pytest.fixture
def invitation_email():
    return "invitado@example.com"


# Path donde se *usa* timezone.now() dentro del servicio, no donde se define.
TIMEZONE_NOW_PATH = "apps.memberships.invitation.domain.services.timezone.now"


def _create_invitation(*, admin_user, email, status=Status.PENDING, hours_offset=0):
    """
    Crea una invitación directamente con InvitationService.create y opcionalmente
    desplaza expires_at hacia el pasado/futuro para simular distintos escenarios,
    sin necesidad de esperar tiempo real.

    InvitationService.create no envía el correo (eso lo hace invite_user),
    así que aquí evitamos disparar el envío real de email en los tests.
    """
    invitation = InvitationService.create(
        email=email, invited_by=admin_user, is_staff=False
    )
    raw_token = invitation.raw_token  # guardado en memoria por InvitationService.create

    if hours_offset != 0:
        invitation.expires_at = timezone.now() + timedelta(hours=hours_offset)
    if status != Status.PENDING:
        invitation.status = status
    invitation.save(update_fields=["expires_at", "status"])

    return invitation, raw_token


@pytest.mark.django_db
class TestValidateToken:
    def test_token_recien_creado_es_valido(self, admin_user, invitation_email):
        invitation, raw_token = _create_invitation(
            admin_user=admin_user, email=invitation_email
        )

        result = InvitationService.validate_token(token=raw_token)

        assert result.pk == invitation.pk
        assert result.status == Status.PENDING

    def test_token_inexistente_lanza_not_found(self):
        with pytest.raises(InvitationNotFound):
            InvitationService.validate_token(token="token-que-no-existe")

    def test_token_expirado_pero_aun_pending_en_bd_se_marca_expired(
        self, admin_user, invitation_email
    ):
        """
        Caso central del bug original: el registro sigue con status=PENDING
        en la BD porque nada lo actualizó automáticamente. validate_token debe
        detectarlo por expires_at, marcarlo EXPIRED en este mismo llamado
        (expiración perezosa) y lanzar InvitationExpired.
        """
        invitation, raw_token = _create_invitation(
            admin_user=admin_user, email=invitation_email, hours_offset=-1
        )
        assert invitation.status == Status.PENDING  # precondición del bug

        with pytest.raises(InvitationExpired):
            InvitationService.validate_token(token=raw_token)

        invitation.refresh_from_db()
        assert invitation.status == Status.EXPIRED

    def test_token_ya_marcado_expired_lanza_expired_sin_volver_a_guardar(
        self, admin_user, invitation_email
    ):
        invitation, raw_token = _create_invitation(
            admin_user=admin_user,
            email=invitation_email,
            status=Status.EXPIRED,
            hours_offset=-1,
        )

        with pytest.raises(InvitationExpired):
            InvitationService.validate_token(token=raw_token)

    def test_token_ya_aceptado_lanza_already_used(self, admin_user, invitation_email):
        invitation, raw_token = _create_invitation(
            admin_user=admin_user, email=invitation_email, status=Status.ACCEPTED
        )

        with pytest.raises(InvitationAlreadyUsed):
            InvitationService.validate_token(token=raw_token)

    def test_token_valido_justo_antes_de_expirar(self, admin_user, invitation_email):
        """
        Verifica el límite exacto usando mock de timezone.now en vez de
        esperar minutos reales: congelamos 'ahora' un segundo antes de
        expires_at y confirmamos que el token todavía es válido.
        """
        invitation, raw_token = _create_invitation(
            admin_user=admin_user, email=invitation_email
        )
        un_segundo_antes = invitation.expires_at - timedelta(seconds=1)

        with patch(TIMEZONE_NOW_PATH, return_value=un_segundo_antes):
            result = InvitationService.validate_token(token=raw_token)

        assert result.status == Status.PENDING

    def test_token_invalido_justo_despues_de_expirar(
        self, admin_user, invitation_email
    ):
        invitation, raw_token = _create_invitation(
            admin_user=admin_user, email=invitation_email
        )
        un_segundo_despues = invitation.expires_at + timedelta(seconds=1)

        with patch(TIMEZONE_NOW_PATH, return_value=un_segundo_despues):
            with pytest.raises(InvitationExpired):
                InvitationService.validate_token(token=raw_token)


@pytest.mark.django_db
class TestAcceptInvitation:
    def test_acepta_invitacion_valida_crea_usuario_y_membership(
        self, admin_user, invitation_email
    ):
        invitation, raw_token = _create_invitation(
            admin_user=admin_user, email=invitation_email
        )

        user = InvitationService.accept_invitation(
            token=raw_token, password="nueva-password-123"
        )

        invitation.refresh_from_db()
        assert invitation.status == Status.ACCEPTED
        assert user.email == invitation_email
        assert Membership.objects.filter(user=user).exists()

    def test_acepta_invitacion_expirada_no_crea_nada(
        self, admin_user, invitation_email
    ):
        invitation, raw_token = _create_invitation(
            admin_user=admin_user, email=invitation_email, hours_offset=-1
        )
        usuarios_antes = User.objects.count()

        with pytest.raises(InvitationExpired):
            InvitationService.accept_invitation(
                token=raw_token, password="nueva-password-123"
            )

        invitation.refresh_from_db()
        assert invitation.status == Status.EXPIRED
        # @transaction.atomic asegura que no quedó un usuario a medio crear
        assert User.objects.count() == usuarios_antes
        assert not Membership.objects.filter(invited_at=invitation.created_at).exists()

    def test_acepta_invitacion_ya_usada_lanza_already_used(
        self, admin_user, invitation_email
    ):
        invitation, raw_token = _create_invitation(
            admin_user=admin_user, email=invitation_email, status=Status.ACCEPTED
        )

        with pytest.raises(InvitationAlreadyUsed):
            InvitationService.accept_invitation(
                token=raw_token, password="otra-password-123"
            )

    def test_acepta_invitacion_con_token_inexistente_lanza_not_found(self):
        with pytest.raises(InvitationNotFound):
            InvitationService.accept_invitation(
                token="token-falso", password="cualquier-password"
            )
