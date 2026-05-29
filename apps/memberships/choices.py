from django.db import models
from django.utils.translation import gettext_lazy as _


class Status(models.TextChoices):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    EXPIRED = "EXPIRED"


class Role(models.TextChoices):
    OWNER = "OWNER", _("Owner")
    ADMIN = "ADMIN", _("Administrator")
    SELLER = "SELLER", _("Seller")
    VIEWER = "VIEWER", _("Viewer")
