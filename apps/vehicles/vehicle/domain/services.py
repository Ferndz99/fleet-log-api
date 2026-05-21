from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import UploadedFile
from django.db import IntegrityError, transaction

from apps.vehicles.vehicle.domain.exceptions import (
    InvalidMediaType,
    MediaNotFound,
    MediaUploadFailed,
    VehicleLogNotFound,
    VehicleNotFound,
    VehiclePatentAlreadyExists,
)
from .models import Media, Vehicle, VehicleLog

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
            )

            if files:
                MediaService.bulk_create(log_id=log.pk, files=files)

        return log

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
