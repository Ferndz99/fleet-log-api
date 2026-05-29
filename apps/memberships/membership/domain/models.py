from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.memberships.choices import Role


class Membership(models.Model):
    """
    Represents the relationship between a user and a company.
    Defines the user's role and status within that company.
    """

    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="membership",
        verbose_name=_("user"),
    )


    is_active = models.BooleanField(
        default=True,
        verbose_name=_("is active"),
        help_text=_("Designates whether this membership is active."),
    )

    invited_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("invited at"),
        help_text=_("Date when the user was invited to the company"),
    )

    joined_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("joined at"),
        help_text=_("Date when the user joined the company"),
    )

    class Meta:
        verbose_name = _("membership")
        verbose_name_plural = _("memberships")

        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["is_active"]),
        ]
        ordering = ["joined_at"]

    def __str__(self) -> str:
        return f"{self.user}"
