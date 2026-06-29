from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.vehicles.choices import VehicleLogStatus, VehicleLogType

User = get_user_model()


class Vehicle(models.Model):
    """
    ES: Representa un activo fundamental de la flota dentro del sistema de gestión de flotas.

    Contiene la identificación básica, los datos de fabricación y los datos operativos
    de cada vehículo. Sirve como entidad principal para el seguimiento de registros,
    expedientes de mantenimiento y archivos adjuntos.

    EN: Represents a core vehicle asset within the fleet management system.

    Mains basic identification, manufacturing details, and operational data
    for each vehicle. Serves as the primary entity for tracking logs,
    maintenance records, and media attachments.
    """

    patent = models.CharField(
        _("patent"),
        max_length=10,
        unique=True,
        help_text=_(
            "Chilean format consisting of 4 letters and 2 numbers (e.g., ABCD12) without hyphens."
        ),
    )
    brand = models.CharField(
        _("brand"),
        max_length=100,
        help_text=_(
            "The commercial name of the vehicle manufacturer (e.g., Toyota, Chevrolet, Ford)."
        ),
    )
    model = models.CharField(
        _("model"),
        max_length=100,
        help_text=_(
            "The specific commercial model or series name of the vehicle (e.g., Corolla, Sail, F-150)."
        ),
    )
    year = models.PositiveSmallIntegerField(
        _("year"),
        help_text=_(
            "The 4-digit manufacturing or model year of the vehicle (e.g., 2024)."
        ),
    )
    created_at = models.DateTimeField(
        _("created at"),
        auto_now_add=True,
        help_text=_(
            "Timestamp automatically recorded by the system when this vehicle entry is created."
        ),
    )

    class Meta:
        verbose_name = _("vehicle")
        verbose_name_plural = _("vehicles")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["patent"], name="vehicle_patent_idx"),
        ]
        permissions = [
            ("search_vehicle_by_patent", _("Can search vehicle by patent")),
        ]

    def __str__(self) -> str:
        return f"{self.brand} {self.model} ({self.year}) — {self.patent}"


class VehicleLog(models.Model):
    """
    ES: Representa un evento, una entrada de mantenimiento o un registro general relacionado con un vehículo concreto.

    EN: Represents an event, maintenance entry, or general log related to a specific vehicle.

    """

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="logs",
        verbose_name=_("vehicle"),
        help_text=_("The vehicle this log entry is associated with."),
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="vehicle_logs",
        verbose_name=_("created by"),
        help_text=_(
            "The user account that recorded this log entry. Automatically cleared if the user is deleted."
        ),
    )
    title = models.CharField(
        _("title"),
        max_length=255,
        help_text=_(
            "A brief summary or headline of the log event (e.g., Routine Oil Change, Brake Noise Issue)."
        ),
    )
    detail = models.TextField(
        _("detail"),
        help_text=_(
            "A comprehensive description of the event, work performed, or observations made."
        ),
    )
    created_at = models.DateTimeField(
        _("created at"),
        auto_now_add=True,
        help_text=_(
            "Timestamp automatically recorded when this log entry was generated."
        ),
    )
    type = models.CharField(
        max_length=30,
        choices=VehicleLogType.choices,
        default=VehicleLogType.OBSERVATION,
        help_text=_(
            "The category of the log entry to help classify the record (e.g., Maintenance, Observation, Incident or Cleaning)."
        ),
    )
    status = models.CharField(
        max_length=30,
        choices=VehicleLogStatus.choices,
        default=VehicleLogStatus.PENDING,
        help_text=_(
            "The current operational state of this log entry (e.g., Pending, Resolved or Reviewed)."
        ),
    )

    class Meta:
        verbose_name = _("vehicle log")
        verbose_name_plural = _("vehicle logs")
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["vehicle", "-created_at"], name="vehiclelog_vehicle_date_idx"
            ),
        ]
        permissions = [("update_vehiclelog_status", _("Can change vehicle log status"))]

    def __str__(self) -> str:
        return f"[{self.vehicle.patent}] {self.title}"


class Media(models.Model):
    """
    ES: Representa un archivo adjunto multimedia (foto o vídeo) subido para una entrada concreta del registro de un vehículo.

    EN: Represents a media attachment (photo or video) uploaded for a specific vehicle log entry.
    """

    class MediaType(models.TextChoices):
        PHOTO = "photo", _("photo")
        VIDEO = "video", _("video")

    vehicle_log = models.ForeignKey(
        VehicleLog,
        on_delete=models.CASCADE,
        related_name="media_files",
        verbose_name=_("vehicle log"),
        help_text=_("The specific vehicle log entry this media file is attached to."),
    )
    file = models.FileField(
        _("file"),
        upload_to="vehicle_logs/%Y/%m/%d/",
        help_text=_(
            "The uploaded file. Supported formats are typically images (JPEG, PNG) or videos (MP4, MOV)."
        ),
    )
    type = models.CharField(
        _("type"),
        max_length=10,
        choices=MediaType.choices,
        help_text=_(
            "The format category of the file, determining how it should be rendered in the interface."
        ),
    )

    class Meta:
        verbose_name = _("media")
        verbose_name_plural = _("media")
        ordering = ["id"]
        indexes = [
            models.Index(fields=["vehicle_log", "type"], name="media_log_type_idx"),
        ]

    def __str__(self) -> str:
        # return f"[{self.get_type_display()}] {_('attachment for log')} #{self.vehicle_log_id}"
        return f"{self.get_type_display()} — Log #{self.vehicle_log_id}" # type: ignore
