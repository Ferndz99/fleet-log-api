from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _

from apps.accounts.user.domain.managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    """
    Modelo de Usuario personalizado que usa email como identificador principal.
    Soporta roles definidos en UserRole.
    """

    email = models.EmailField(_("email address"), unique=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:  # type: ignore
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        ordering = ["-created_at"]

    def __str__(self):
        return self.email
