from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class Profile(models.Model):
    """
    Perfil extendido del usuario con información personal adicional.
    Relación 1:1 con el modelo User.
    """

    # --- Relación ---
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name=_("user"),
    )

    # --- Nombre ---
    first_name = models.CharField(_("first name"), max_length=100)
    last_name = models.CharField(_("last name"), max_length=100)
    second_last_name = models.CharField(
        _("second last name"), max_length=100, blank=True, default=""
    )

    # --- Identificación (contexto chileno) ---
    rut = models.CharField(_("RUT"), max_length=12, unique=True)

    # --- Contacto ---
    phone = models.CharField(_("phone number"), max_length=20, blank=True, default="")

    # --- Sugerencias adicionales ---
    birth_date = models.DateField(_("birth date"), blank=True, null=True)
    avatar = models.ImageField(
        _("avatar"), upload_to="profiles/avatars/", blank=True, null=True, default="default/avatar.png"
    )
    address = models.CharField(_("address"), max_length=255, blank=True, default="")

    # --- Timestamps ---
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # type: ignore
        verbose_name = _("Profile")
        verbose_name_plural = _("Profiles")
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.user.email})"

    @property
    def full_name(self) -> str:
        parts = [self.first_name, self.last_name]
        if self.second_last_name:
            parts.append(self.second_last_name)
        return " ".join(parts)
