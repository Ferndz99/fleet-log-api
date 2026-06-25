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
    """Handles all business logic related to Vehicle."""

    @staticmethod
    def get_by_id(vehicle_id: int) -> Vehicle:
        try:
            return Vehicle.objects.get(pk=vehicle_id)
        except Vehicle.DoesNotExist:
            raise VehicleNotFound(vehicle_id=vehicle_id)

    @staticmethod
    def list_all() -> list[Vehicle]:
        return list(Vehicle.objects.all())

    @staticmethod
    def create(*, patent: str, brand: str, model: str, year: int) -> Vehicle:
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
        vehicle = VehicleService.get_by_id(vehicle_id)
        vehicle.delete()

    @staticmethod
    def get_by_patent(patent: str) -> Vehicle:
        try:
            return Vehicle.objects.get(patent__iexact=patent)
        except Vehicle.DoesNotExist:
            raise VehiclePatentNotFound(patent=patent)


class VehicleLogService:
    """Handles all business logic related to VehicleLog."""

    @staticmethod
    def get_by_id(vehicle_id: int, log_id: int) -> VehicleLog:
        try:
            return VehicleLog.objects.select_related("vehicle", "created_by").get(
                pk=log_id,
                vehicle_id=vehicle_id,
            )
        except VehicleLog.DoesNotExist:
            raise VehicleLogNotFound(log_id=log_id, vehicle_id=vehicle_id)

    @staticmethod
    def list_by_vehicle(vehicle_id: int) -> list[VehicleLog]:
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
        log = VehicleLogService.get_by_id(vehicle_id, log_id)

        if title is not None:
            log.title = title.strip()
        if detail is not None:
            log.detail = detail.strip()

        log.save()
        return log

    @staticmethod
    def delete(vehicle_id: int, log_id: int) -> None:
        log = VehicleLogService.get_by_id(vehicle_id, log_id)
        log.delete()

    @staticmethod
    def update_status(
        vehicle_id: int,
        log_id: int,
        *,
        status: VehicleLogStatus,
    ) -> VehicleLog:
        log = VehicleLogService.get_by_id(vehicle_id, log_id)
        log.status = status
        log.save(update_fields=["status"])
        return log


class MediaService:
    """Handles all business logic related to Media files."""

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
        try:
            return Media.objects.select_related("vehicle_log").get(pk=media_id)
        except Media.DoesNotExist:
            raise MediaNotFound(media_id=media_id)

    @staticmethod
    def list_by_log(vehicle_id: int, log_id: int) -> list[Media]:
        VehicleLogService.get_by_id(vehicle_id, log_id)  # validates ownership
        return list(Media.objects.filter(vehicle_log_id=log_id))

    @staticmethod
    def _resolve_type(file: UploadedFile) -> Media.MediaType:
        extension = file.name.rsplit(".", 1)[-1].lower() if "." in file.name else ""
        media_type = MediaService._VALID_EXTENSIONS.get(extension)
        if media_type is None:
            raise InvalidMediaType(media_type=extension or file.name)
        return media_type

    @staticmethod
    def create(log_id: int, *, file: UploadedFile) -> Media:
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
        created: list[Media] = []
        with transaction.atomic():
            for file in files:
                created.append(MediaService.create(log_id=log_id, file=file))
        return created

    @staticmethod
    def delete(media_id: int) -> None:
        media = MediaService.get_by_id(media_id)
        media.file.delete(save=False)  # removes the physical file from storage
        media.delete()


TOP_VEHICLES_LIMIT = 5
TOP_USERS_LIMIT = 5
RECENT_LOGS_LIMIT = 10


class DashboardService:
    """Builds aggregated statistics for the admin dashboard."""

    @staticmethod
    def get_dashboard_data(
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict:
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
        qs = VehicleLog.objects.all()
        if date_from is not None:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to is not None:
            qs = qs.filter(created_at__date__lte=date_to)
        return qs

    # --- Summary ---

    @staticmethod
    def _get_summary(logs_qs) -> dict:
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
        media_qs = Media.objects.filter(vehicle_log__in=logs_qs)
        logs_without_media = logs_qs.filter(media_files__isnull=True).distinct().count()

        return {
            "total_media": media_qs.count(),
            "photos": media_qs.filter(type=Media.MediaType.PHOTO).count(),
            "videos": media_qs.filter(type=Media.MediaType.VIDEO).count(),
            "logs_without_media": logs_without_media,
        }
