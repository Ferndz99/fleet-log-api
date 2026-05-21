from django.contrib.auth.models import BaseUserManager
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """
    Manager personalizado para el modelo User.
    Maneja la creación de usuarios y superusuarios con validaciones.
    """

    def create_user(
        self, email: str, password: str | None = None, **extra_fields
    ) -> "User":  # noqa: F821
        """
        Crea y guarda un usuario con el email y contraseña dados.
        """
        if not email:
            raise ValueError(_("El email es obligatorio."))

        email = self.normalize_email(email)

        # Valores por defecto para usuario estándar
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(
        self, email: str, password: str | None = None, **extra_fields
    ) -> "User":  # noqa: F821
        """
        Crea y guarda un superusuario con rol de ADMIN.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(email, password, **extra_fields)
