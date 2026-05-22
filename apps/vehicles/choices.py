from django.db import models

class VehicleLogType(models.TextChoices):
    INCIDENT = "incident", "Incident"
    MAINTENANCE = "maintenance", "Maintenance"
    OBSERVATION = "observation", "Observation"
    CLEANING = "cleaning", "Cleaning"


class VehicleLogStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    REVIEWED = "reviewed", "Reviewed"
    RESOLVED = "resolved", "Resolved"


class SeverityLevel(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"
