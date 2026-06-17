from django.utils import timezone

from django.db import models

from apps.memberships.choices import Role, Status


class Invitation(models.Model):
    email = models.EmailField()

    token_hash = models.CharField(max_length=64, unique=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    is_staff = models.BooleanField(default=False)

    invited_by = models.ForeignKey("accounts.User", on_delete=models.PROTECT)

    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return self.expires_at < timezone.now()
