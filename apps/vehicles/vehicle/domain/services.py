from __future__ import annotations
from datetime import date, timedelta

from django.db.models import Count, Q
from django.utils import timezone

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import UploadedFile
from django.db import IntegrityError, transaction

from apps.vehicles.choices import VehicleLogStatus, VehicleLogType
from apps.vehicles.vehicle.domain.exceptions import (
    InvalidMediaType,
    MediaNotFound,
    MediaUploadFailed,
    VehicleLogNotFound,
    VehicleNotFound,
    VehiclePatentAlreadyExists,
    VehiclePatentNotFound,
)
from .models import Media, Vehicle, VehicleLog

from django.db.models import Count, F, Value
from django.db.models.functions import Concat, Coalesce

User = get_user_model()


class VehicleService:
    """
    ES: Proporciona la lógica de negocio y las operaciones necesarias para gestionar los vehículos de la flota.

    Actúa como capa de servicio entre las vistas/serializadores y el modelo «Vehículo»,
    encapsulando la validación, la normalización de datos y la gestión de excepciones.

    EN: Provides business logic and operations for managing fleet vehicles.

    Acts as the service layer between the views/serializers and the Vehicle model,
    encapsulating validation, data normalization, and exception handling.

    """

    @staticmethod
    def get_by_id(vehicle_id: int) -> Vehicle:
        """Retrieves a single vehicle instance by its primary key.

        Args:
            vehicle_id (int): The unique identifier of the vehicle.

        Returns:
            Vehicle: The requested vehicle model instance.

        Raises:
            VehicleNotFound: If no vehicle matches the provided ID.
        """
        try:
            return Vehicle.objects.get(pk=vehicle_id)
        except Vehicle.DoesNotExist:
            raise VehicleNotFound(vehicle_id=vehicle_id)

    @staticmethod
    def list_all() -> list[Vehicle]:
        """Retrieves all vehicle records from the database.

        Returns:
            list[Vehicle]: A list containing all vehicle instances.
        """
        return list(Vehicle.objects.all())

    @staticmethod
    def create(*, patent: str, brand: str, model: str, year: int) -> Vehicle:
        """Creates and sanitizes a new vehicle record in the system.

        Args:
            patent (str): The unique license plate or patent identifier.
            brand (str): The name of the vehicle manufacturer.
            model (str): The specific model or series name.
            year (int): The manufacturing or model year.

        Returns:
            Vehicle: The newly created and saved vehicle instance.

        Raises:
            VehiclePatentAlreadyExists: If the patent is already registered.
        """
        try:
            vehicle = Vehicle.objects.create(
                patent=patent.upper().strip(),
                brand=brand.strip(),
                model=model.strip(),
                year=year,
            )
        except IntegrityError:
            raise VehiclePatentAlreadyExists(patent=patent)

        return vehicle

    @staticmethod
    def update(
        vehicle_id: int,
        *,
        patent: str | None = None,
        brand: str | None = None,
        model: str | None = None,
        year: int | None = None,
    ) -> Vehicle:
        """Updates specific fields of an existing vehicle.

        Only updates the fields that are explicitly provided (not None). It performs
        uniqueness checks if the patent is being changed.

        Args:
            vehicle_id (int): The unique identifier of the vehicle to update.
            patent (str | None, optional): New license plate value. Defaults to None.
            brand (str | None, optional): New manufacturer name. Defaults to None.
            model (str | None, optional): New series/model name. Defaults to None.
            year (int | None, optional): New manufacturing year. Defaults to None.

        Returns:
            Vehicle: The updated vehicle instance.

        Raises:
            VehicleNotFound: If the vehicle_id does not exist.
            VehiclePatentAlreadyExists: If the new patent conflicts with another vehicle.
        """
        vehicle = VehicleService.get_by_id(vehicle_id)

        if patent is not None:
            patent = patent.upper().strip()
            if (
                patent != vehicle.patent
                and Vehicle.objects.filter(patent=patent).exists()
            ):
                raise VehiclePatentAlreadyExists(patent=patent)
            vehicle.patent = patent

        if brand is not None:
            vehicle.brand = brand.strip()
        if model is not None:
            vehicle.model = model.strip()
        if year is not None:
            vehicle.year = year

        vehicle.save()
        return vehicle

    @staticmethod
    def delete(vehicle_id: int) -> None:
        """Deletes a vehicle record from the database.

        Args:
            vehicle_id (int): The unique identifier of the vehicle to be removed.

        Raises:
            VehicleNotFound: If no vehicle matches the provided ID.
        """
        vehicle = VehicleService.get_by_id(vehicle_id)
        vehicle.delete()

    @staticmethod
    def get_by_patent(patent: str) -> Vehicle:
        """Finds a vehicle using a case-insensitive lookup on its patent.

        Args:
            patent (str): The license plate string to search for.

        Returns:
            Vehicle: The matching vehicle instance.

        Raises:
            VehiclePatentNotFound: If no vehicle matches the provided patent.
        """
        try:
            return Vehicle.objects.get(patent__iexact=patent)
        except Vehicle.DoesNotExist:
            raise VehiclePatentNotFound(patent=patent)


class VehicleLogService:
    """Provides business logic and atomicity for managing vehicle event logs.

    Handles CRUD operations, query optimization (select_related), status updates,
    and bulk media file attachments bound to specific vehicle events.
    """

    @staticmethod
    def get_by_id(vehicle_id: int, log_id: int) -> VehicleLog:
        """Retrieves a specific vehicle log entry verifying its relationship.

        Optimizes database performance by fetching related 'vehicle' and
        'created_by' tables in a single SQL JOIN query.

        Args:
            vehicle_id (int): The primary key of the associated vehicle.
            log_id (int): The primary key of the log entry.

        Returns:
            VehicleLog: The requested vehicle log instance.

        Raises:
            VehicleLogNotFound: If no log entry matches the provided parameters.
        """
        try:
            return VehicleLog.objects.select_related("vehicle", "created_by").get(
                pk=log_id,
                vehicle_id=vehicle_id,
            )
        except VehicleLog.DoesNotExist:
            raise VehicleLogNotFound(log_id=log_id, vehicle_id=vehicle_id)

    @staticmethod
    def list_by_vehicle(vehicle_id: int) -> list[VehicleLog]:
        """Retrieves all log records belonging to a particular vehicle.

        Validates the vehicle's existence before running the filter query.

        Args:
            vehicle_id (int): The unique identifier of the target vehicle.

        Returns:
            list[VehicleLog]: A list of logs sorted by Meta configuration.

        Raises:
            VehicleNotFound: If the provided vehicle_id does not exist.
        """
        VehicleService.get_by_id(vehicle_id)  # raises VehicleNotFound if missing
        return list(
            VehicleLog.objects.select_related("created_by").filter(
                vehicle_id=vehicle_id
            )
        )

    @staticmethod
    def create(
        vehicle_id: int,
        *,
        title: str,
        detail: str,
        type: VehicleLogType,
        status: VehicleLogStatus,
        created_by: User | None = None,
        files: list[UploadedFile] | None = None,
    ) -> VehicleLog:
        """Creates a vehicle log and registers its media files atomically.

        Args:
            vehicle_id (int): The unique identifier of the vehicle.
            title (str): Headline summary of the log entry.
            detail (str): In-depth text description of the event.
            type (VehicleLogType): Category choice for the event.
            status (VehicleLogStatus): Initial operational status choice.
            created_by (User | None, optional): User who recorded the log. Defaults to None.
            files (list[UploadedFile] | None, optional): Raw physical files to upload. Defaults to None.

        Returns:
            VehicleLog: The fully generated log instance with its relations.

        Raises:
            VehicleNotFound: If the associated vehicle doesn't exist.
        """
        vehicle = VehicleService.get_by_id(vehicle_id)

        with transaction.atomic():
            log = VehicleLog.objects.create(
                vehicle=vehicle,
                created_by=created_by,
                title=title.strip(),
                detail=detail.strip(),
                type=type,
                status=status,
            )

            if files:
                MediaService.bulk_create(log_id=log.pk, files=files)

        return log

    # CONSIDERAR QUE TAN VALIDO ES MANTENER LA FUNCION DE ACTUALIZACION DE UN LOG. LOG INMUTABLE(?)
    @staticmethod
    def update(
        vehicle_id: int,
        log_id: int,
        *,
        title: str | None = None,
        detail: str | None = None,
    ) -> VehicleLog:
        """Updates basic textual descriptive attributes of a log record.

        Args:
            vehicle_id (int): The primary key of the associated vehicle.
            log_id (int): The primary key of the log entry to update.
            title (str | None, optional): New title summary string. Defaults to None.
            detail (str | None, optional): New comprehensive detail string. Defaults to None.

        Returns:
            VehicleLog: The updated log model instance.

        Raises:
            VehicleLogNotFound: If the combination of log and vehicle does not exist.
        """
        log = VehicleLogService.get_by_id(vehicle_id, log_id)

        if title is not None:
            log.title = title.strip()
        if detail is not None:
            log.detail = detail.strip()

        log.save()
        return log

    @staticmethod
    def delete(vehicle_id: int, log_id: int) -> None:
        """Deletes a log record from the database.

        Args:
            vehicle_id (int): The primary key of the associated vehicle.
            log_id (int): The primary key of the log entry to delete.

        Raises:
            VehicleLogNotFound: If the log does not match the identifiers.
        """
        log = VehicleLogService.get_by_id(vehicle_id, log_id)
        log.delete()

    @staticmethod
    def update_status(
        vehicle_id: int,
        log_id: int,
        *,
        status: VehicleLogStatus,
    ) -> VehicleLog:
        """Changes the current workflow state of the log entry.

        Optimizes the SQL database call by committing only the 'status' field.

        Args:
            vehicle_id (int): The primary key of the associated vehicle.
            log_id (int): The primary key of the log entry.
            status (VehicleLogStatus): The new state value to be applied.

        Returns:
            VehicleLog: The modified log model instance.

        Raises:
            VehicleLogNotFound: If the log entry is not found.
        """
        log = VehicleLogService.get_by_id(vehicle_id, log_id)
        log.status = status
        log.save(update_fields=["status"])
        return log


class MediaService:
    """Handles business logic, validation, and storage operations for Media files.

    Manages single and bulk file uploads, maps file extensions to operational
    media types (photo/video), optimizes spatial queries, and handles physical
    file removal from storage.
    """

    _VALID_EXTENSIONS: dict[str, Media.MediaType] = {
        "jpg": Media.MediaType.PHOTO,
        "jpeg": Media.MediaType.PHOTO,
        "png": Media.MediaType.PHOTO,
        "webp": Media.MediaType.PHOTO,
        "mp4": Media.MediaType.VIDEO,
        "mov": Media.MediaType.VIDEO,
        "avi": Media.MediaType.VIDEO,
    }

    @staticmethod
    def get_by_id(media_id: int) -> Media:
        """Retrieves a single media record by its ID.

        Optimizes the database lookup by pre-fetching the related vehicle log entry.

        Args:
            media_id (int): The unique identifier of the media record.

        Returns:
            Media: The requested media model instance.

        Raises:
            MediaNotFound: If no media record matches the provided ID.
        """
        try:
            return Media.objects.select_related("vehicle_log").get(pk=media_id)
        except Media.DoesNotExist:
            raise MediaNotFound(media_id=media_id)

    @staticmethod
    def list_by_log(vehicle_id: int, log_id: int) -> list[Media]:
        """Retrieves all media attachments belonging to a specific vehicle log entry.

        Validates vehicle ownership and log existence prior to filtering.

        Args:
            vehicle_id (int): The primary key of the associated vehicle.
            log_id (int): The primary key of the targeted vehicle log.

        Returns:
            list[Media]: A list containing all matching media model instances.

        Raises:
            VehicleLogNotFound: If the log does not exist or belong to the vehicle.
        """
        VehicleLogService.get_by_id(vehicle_id, log_id)  # validates ownership
        return list(Media.objects.filter(vehicle_log_id=log_id))

    @staticmethod
    def _resolve_type(file: UploadedFile) -> Media.MediaType:
        """Extracts and evaluates the file extension to match a valid Media format.

        Args:
            file (UploadedFile): The raw uploaded file object containing a name attribute.

        Returns:
            Media.MediaType: The resolved inner structural format choice (photo or video).

        Raises:
            InvalidMediaType: If the file extension is missing or not supported.
        """
        extension = file.name.rsplit(".", 1)[-1].lower() if "." in file.name else ""
        media_type = MediaService._VALID_EXTENSIONS.get(extension)
        if media_type is None:
            raise InvalidMediaType(media_type=extension or file.name)
        return media_type

    @staticmethod
    def create(log_id: int, *, file: UploadedFile) -> Media:
        """Validates and persists a single media attachment in the system.

        Args:
            log_id (int): The unique database identifier of the target vehicle log.
            file (UploadedFile): The raw file stream payload to upload.

        Returns:
            Media: The newly generated and saved media model entry.

        Raises:
            InvalidMediaType: If the file type verification fails.
            MediaUploadFailed: If any underlying storage or database transaction fails.
        """
        media_type = MediaService._resolve_type(file)
        try:
            return Media.objects.create(
                vehicle_log_id=log_id,
                file=file,
                type=media_type,
            )
        except Exception as exc:
            raise MediaUploadFailed() from exc

    @staticmethod
    def bulk_create(log_id: int, *, files: list[UploadedFile]) -> list[Media]:
        """Atomically processes and uploads multiple media attachments.

        If one file fails type validation or upload constraints, the entire batch
        is rolled back to maintain structural consistency.

        Args:
            log_id (int): The unique database identifier of the target vehicle log.
            files (list[UploadedFile]): A sequence containing raw upload file payloads.

        Returns:
            list[Media]: A list containing all newly created media model entries.
        """
        created: list[Media] = []
        with transaction.atomic():
            for file in files:
                created.append(MediaService.create(log_id=log_id, file=file))
        return created

    @staticmethod
    def delete(media_id: int) -> None:
        """Removes a media record from the database and deletes its physical file asset.

        Ensures that storage allocation is freed by purging the actual file from the
        configured storage engine (S3, local disk, etc.) alongside the DB record row.

        Args:
            media_id (int): The unique identifier of the target media file.

        Raises:
            MediaNotFound: If the media_id does not map to any record.
        """
        media = MediaService.get_by_id(media_id)
        media.file.delete(save=False)  # removes the physical file from storage
        media.delete()


TOP_VEHICLES_LIMIT = 5
TOP_USERS_LIMIT = 5
RECENT_LOGS_LIMIT = 10


class DashboardService:
    """Builds aggregated statistics and metrics for the administration dashboard.

    Processes analytical data across vehicles, logs, user profiles, and media
    attachments, supporting optional date range filtering for trend analysis.
    """

    @staticmethod
    def get_dashboard_data(
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict:
        """Assembles the complete dashboard payload containing summaries, rankings, and trends.

        Args:
            date_from (date | None, optional): Start date boundary for analytical metrics. Defaults to None.
            date_to (date | None, optional): End date boundary for analytical metrics. Defaults to None.

        Returns:
            dict: Structured nested data containing summary, logs_by_status, logs_by_type,
                  logs_by_type_and_status, top_vehicles_by_logs, top_users_by_logs,
                  recent_logs, and media_summary.
        """
        logs_qs = DashboardService._get_logs_queryset(date_from, date_to)

        return {
            "summary": DashboardService._get_summary(logs_qs),
            "logs_by_status": DashboardService._get_logs_by_status(logs_qs),
            "logs_by_type": DashboardService._get_logs_by_type(logs_qs),
            "logs_by_type_and_status": DashboardService._get_logs_by_type_and_status(
                logs_qs
            ),
            "top_vehicles_by_logs": DashboardService._get_top_vehicles(logs_qs),
            "top_users_by_logs": DashboardService._get_top_users(logs_qs),
            "recent_logs": DashboardService._get_recent_logs(logs_qs),
            "media_summary": DashboardService._get_media_summary(logs_qs),
        }

    # --- Queryset base ---

    @staticmethod
    def _get_logs_queryset(date_from: date | None, date_to: date | None):
        """Generates a base vehicle log QuerySet filtered by an optional date range.

        Args:
            date_from (date | None): Lower bound constraint for the log creation date.
            date_to (date | None): Upper bound constraint for the log creation date.

        Returns:
            QuerySet: Evaluated or lazy vehicle log query with applied date filters.
        """
        qs = VehicleLog.objects.all()
        if date_from is not None:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to is not None:
            qs = qs.filter(created_at__date__lte=date_to)
        return qs

    # --- Summary ---

    @staticmethod
    def _get_summary(logs_qs) -> dict:
        """Calculates global totals, current real-time progress counters, and critical bottlenecks.

        Real-time counters (today, this week, this month) evaluate the total historical records
        and ignore the dashboard's filtering date boundaries to preserve operational awareness.

        Args:
            logs_qs (QuerySet): Base query containing logs within the filtered date range.

        Returns:
            dict: High-level KPI values including total vehicles, filtered logs, status-specific counts,
                  and calendar milestones.
        """
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        # logs_today/this_week/this_month always reflect "now",
        # independent of date_from/date_to (esos son trend indicators,
        # no parte del rango filtrado).
        all_logs = VehicleLog.objects.all()

        return {
            "total_vehicles": Vehicle.objects.count(),
            "total_logs": logs_qs.count(),
            "logs_today": all_logs.filter(created_at__date=today).count(),
            "logs_this_week": all_logs.filter(created_at__date__gte=week_start).count(),
            "logs_this_month": all_logs.filter(
                created_at__date__gte=month_start
            ).count(),
            "pending_logs": logs_qs.filter(status=VehicleLogStatus.PENDING).count(),
            "pending_incidents": logs_qs.filter(
                status=VehicleLogStatus.PENDING,
                type=VehicleLogType.INCIDENT,
            ).count(),
        }

    # --- Distribuciones ---

    @staticmethod
    def _get_logs_by_status(logs_qs) -> list[dict]:
        """Groups and counts the log distribution across all defined workflow statuses.

        Ensures that statuses with zero matching records are explicitly included with a count of 0.

        Args:
            logs_qs (QuerySet): Filtered log data source.

        Returns:
            list[dict]: List of items mapping the status choice value, its localized label, and frequency count.
        """
        counts = dict(
            logs_qs.values_list("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        )
        return [
            {"status": value, "label": label, "count": counts.get(value, 0)}
            for value, label in VehicleLogStatus.choices
        ]

    @staticmethod
    def _get_logs_by_type(logs_qs) -> list[dict]:
        """Groups and counts the log distribution across all defined event categories.

        Ensures that category types with zero records are included with a count of 0.

        Args:
            logs_qs (QuerySet): Filtered log data source.

        Returns:
            list[dict]: List of items mapping the type choice value, its localized label, and frequency count.
        """
        counts = dict(
            logs_qs.values_list("type")
            .annotate(count=Count("id"))
            .values_list("type", "count")
        )
        return [
            {"type": value, "label": label, "count": counts.get(value, 0)}
            for value, label in VehicleLogType.choices
        ]

    @staticmethod
    def _get_logs_by_type_and_status(logs_qs) -> list[dict]:
        """Performs cross-tabulation metrics to map statuses inside each log category type.

        Args:
            logs_qs (QuerySet): Filtered log data source.

        Returns:
            list[dict]: List structured by event type, enclosing a nested dictionary matrix of status counters.
        """
        raw = logs_qs.values("type", "status").annotate(count=Count("id"))

        lookup: dict[str, dict[str, int]] = {}
        for row in raw:
            lookup.setdefault(row["type"], {})[row["status"]] = row["count"]

        return [
            {
                "type": type_value,
                "label": type_label,
                "statuses": {
                    status_value: lookup.get(type_value, {}).get(status_value, 0)
                    for status_value, _ in VehicleLogStatus.choices
                },
            }
            for type_value, type_label in VehicleLogType.choices
        ]

    # --- Rankings ---

    @staticmethod
    def _get_top_vehicles(logs_qs) -> list[dict]:
        """Ranks the most active vehicles based on the volume of generated log events.

        Args:
            logs_qs (QuerySet): Filtered log data source.

        Returns:
            list[dict]: Serialized representation of high-frequency vehicles, limited by TOP_VEHICLES_LIMIT.
        """
        top = (
            logs_qs.values(
                "vehicle_id", "vehicle__patent", "vehicle__brand", "vehicle__model"
            )
            .annotate(log_count=Count("id"))
            .order_by("-log_count")[:TOP_VEHICLES_LIMIT]
        )
        return [
            {
                "id": row["vehicle_id"],
                "patent": row["vehicle__patent"],
                "brand": row["vehicle__brand"],
                "model": row["vehicle__model"],
                "log_count": row["log_count"],
            }
            for row in top
        ]

    # @staticmethod
    # def _get_top_users(logs_qs) -> list[dict]:
    #     top = (
    #         logs_qs.exclude(created_by__isnull=True)
    #         .values("created_by_id", "created_by__email")
    #         .annotate(log_count=Count("id"))
    #         .order_by("-log_count")[:TOP_USERS_LIMIT]
    #     )
    #     return [
    #         {
    #             "id": row["created_by_id"],
    #             "email": row["created_by__email"],
    #             "log_count": row["log_count"],
    #         }
    #         for row in top
    #     ]
    @staticmethod
    def _get_top_users(logs_qs) -> list[dict]:
        """Ranks user accounts by the total number of log entries they have submitted.

        Uses database functions (Concat, Coalesce) to compute and sanitize full name fields
        directly within the SQL engine execution context.

        Args:
            logs_qs (QuerySet): Filtered log data source.

        Returns:
            list[dict]: Serialized user profile summary data, limited by TOP_USERS_LIMIT.
        """
        top = (
            logs_qs.exclude(created_by__isnull=True)
            .values("created_by_id")
            .annotate(
                email=F("created_by__email"),
                full_name=Concat(
                    "created_by__profile__first_name",
                    Value(" "),
                    "created_by__profile__last_name",
                    Value(" "),
                    Coalesce("created_by__profile__second_last_name", Value("")),
                ),
                log_count=Count("id"),
            )
            .order_by("-log_count")[:TOP_USERS_LIMIT]
        )

        return [
            {
                "id": row["created_by_id"],
                "email": row["email"],
                "full_name": row["full_name"].strip(),
                "log_count": row["log_count"],
            }
            for row in top
        ]

    # --- Actividad reciente ---

    @staticmethod
    def _get_recent_logs(logs_qs) -> list[dict]:
        """Fetches chronological audit trail items for real-time tracking feeds.

        Optimizes database throughput by triggering database JOIN execution via select_related
        and aggregates media attachment metrics per item.

        Args:
            logs_qs (QuerySet): Filtered log data source.

        Returns:
            list[dict]: Chronological slice of log rows, limited by RECENT_LOGS_LIMIT.
        """
        logs = (
            logs_qs.select_related("vehicle", "created_by")
            .annotate(media_count=Count("media_files"))
            .order_by("-created_at")[:RECENT_LOGS_LIMIT]
        )
        return [
            {
                "id": log.id,
                "title": log.title,
                "type": log.type,
                "status": log.status,
                "created_at": log.created_at,
                "vehicle": {"id": log.vehicle_id, "patent": log.vehicle.patent},
                "created_by": (
                    {"id": log.created_by_id, "email": log.created_by.email}
                    if log.created_by_id
                    else None
                ),
                "media_count": log.media_count,
            }
            for log in logs
        ]

    # --- Multimedia ---

    @staticmethod
    def _get_media_summary(logs_qs) -> dict:
        """Aggregates metrics related to uploaded files attached to the active log subset.

        Calculates distribution totals by core media extensions and isolates log entries
        lacking verification attachments.

        Args:
            logs_qs (QuerySet): Filtered log data source.

        Returns:
            dict: Media metric indicators including total_media, photo/video subsets,
                  and logs_without_media counts.
        """
        media_qs = Media.objects.filter(vehicle_log__in=logs_qs)
        logs_without_media = logs_qs.filter(media_files__isnull=True).distinct().count()

        return {
            "total_media": media_qs.count(),
            "photos": media_qs.filter(type=Media.MediaType.PHOTO).count(),
            "videos": media_qs.filter(type=Media.MediaType.VIDEO).count(),
            "logs_without_media": logs_without_media,
        }
