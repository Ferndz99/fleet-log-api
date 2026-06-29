from django.db import models
from django.utils.translation import gettext_lazy as _


class VehicleLogType(models.TextChoices):
    INCIDENT = "incident", _("Incident")
    MAINTENANCE = "maintenance", _("Maintenance")
    OBSERVATION = "observation", _("Observation")
    CLEANING = "cleaning", _("Cleaning")


class VehicleLogStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    REVIEWED = "reviewed", _("Reviewed")
    RESOLVED = "resolved", _("Resolved")


class SeverityLevel(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"
