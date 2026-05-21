from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class Vehicle(models.Model):
    patent = models.CharField(
        _("patent"),
        max_length=10,
        unique=True,
    )
    brand = models.CharField(_("brand"), max_length=100)
    model = models.CharField(_("model"), max_length=100)
    year = models.PositiveSmallIntegerField(_("year"))
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("vehicle")
        verbose_name_plural = _("vehicles")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["patent"], name="vehicle_patent_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.brand} {self.model} ({self.year}) — {self.patent}"


class VehicleLog(models.Model):
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="logs",
        verbose_name=_("vehicle"),
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="vehicle_logs",
        verbose_name=_("created by"),
    )
    title = models.CharField(_("title"), max_length=255)
    detail = models.TextField(_("detail"))
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("vehicle log")
        verbose_name_plural = _("vehicle logs")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["vehicle", "-created_at"], name="vehiclelog_vehicle_date_idx"),
        ]

    def __str__(self) -> str:
        return f"[{self.vehicle.patent}] {self.title}"


class Media(models.Model):
    class MediaType(models.TextChoices):
        PHOTO = "photo", _("Photo")
        VIDEO = "video", _("Video")

    vehicle_log = models.ForeignKey(
        VehicleLog,
        on_delete=models.CASCADE,
        related_name="media_files",
        verbose_name=_("vehicle log"),
    )
    file = models.FileField(_("file"), upload_to="vehicle_logs/%Y/%m/%d/")
    type = models.CharField(
        _("type"),
        max_length=10,
        choices=MediaType.choices,
    )

    class Meta:
        verbose_name = _("media")
        verbose_name_plural = _("media")
        ordering = ["id"]
        indexes = [
            models.Index(fields=["vehicle_log", "type"], name="media_log_type_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.get_type_display()} — Log #{self.vehicle_log_id}"