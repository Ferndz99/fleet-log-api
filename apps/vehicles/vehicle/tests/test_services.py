"""
Tests for VehicleService, VehicleLogService and MediaService.

Run with:
    pytest apps/<your_app>/tests/test_services.py -v
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch, MagicMock

from apps.vehicles.vehicle.domain.exceptions import (
    InvalidMediaType,
    MediaNotFound,
    VehicleLogNotFound,
    VehicleNotFound,
    VehiclePatentAlreadyExists,
)
from apps.vehicles.vehicle.domain.models import Media, Vehicle, VehicleLog
from apps.vehicles.vehicle.domain.services import (
    MediaService,
    VehicleLogService,
    VehicleService,
)

User = get_user_model()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_uploaded_file(filename: str, content: bytes = b"data") -> SimpleUploadedFile:
    return SimpleUploadedFile(name=filename, content=content)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    return User.objects.create_user(email="operator@example.com", password="secret")


@pytest.fixture
def vehicle(db):
    return Vehicle.objects.create(
        patent="ABC123",
        brand="Toyota",
        model="Corolla",
        year=2022,
    )


@pytest.fixture
def vehicle_log(vehicle, user):
    return VehicleLog.objects.create(
        vehicle=vehicle,
        created_by=user,
        title="Initial inspection",
        detail="No visible damage.",
    )


@pytest.fixture
def media(vehicle_log):
    return Media.objects.create(
        vehicle_log=vehicle_log,
        file="vehicle_logs/2024/01/01/front.jpg",
        type=Media.MediaType.PHOTO,
    )


# ---------------------------------------------------------------------------
# VehicleService
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestVehicleService:
    # --- get_by_id ---

    def test_get_by_id_returns_vehicle(self, vehicle):
        result = VehicleService.get_by_id(vehicle.pk)
        assert result == vehicle

    def test_get_by_id_raises_not_found(self):
        with pytest.raises(VehicleNotFound) as exc_info:
            VehicleService.get_by_id(999)
        assert exc_info.value.status_code == 404

    # --- list_all ---

    def test_list_all_returns_all_vehicles(self, vehicle):
        Vehicle.objects.create(patent="XYZ789", brand="Honda", model="Civic", year=2021)
        result = VehicleService.list_all()
        assert len(result) == 2

    def test_list_all_empty(self, db):
        assert VehicleService.list_all() == []

    # --- create ---

    def test_create_normalizes_patent_to_uppercase(self, db):
        vehicle = VehicleService.create(
            patent="abc123", brand="Ford", model="Focus", year=2020
        )
        assert vehicle.patent == "ABC123"

    def test_create_strips_whitespace(self, db):
        vehicle = VehicleService.create(
            patent=" GHI456 ", brand=" Kia ", model=" Rio ", year=2019
        )
        assert vehicle.patent == "GHI456"
        assert vehicle.brand == "Kia"
        assert vehicle.model == "Rio"

    def test_create_raises_on_duplicate_patent(self, vehicle):
        with pytest.raises(VehiclePatentAlreadyExists) as exc_info:
            VehicleService.create(
                patent="ABC123", brand="Other", model="Car", year=2020
            )
        assert exc_info.value.status_code == 409

    # --- update ---

    def test_update_single_field(self, vehicle):
        updated = VehicleService.update(vehicle.pk, brand="Nissan")
        assert updated.brand == "Nissan"
        assert updated.model == vehicle.model  # unchanged

    def test_update_multiple_fields(self, vehicle):
        updated = VehicleService.update(vehicle.pk, brand="Mazda", year=2023)
        assert updated.brand == "Mazda"
        assert updated.year == 2023

    def test_update_patent_normalizes_to_uppercase(self, vehicle):
        updated = VehicleService.update(vehicle.pk, patent="new999")
        assert updated.patent == "NEW999"

    def test_update_patent_to_same_value_is_allowed(self, vehicle):
        updated = VehicleService.update(vehicle.pk, patent="ABC123")
        assert updated.patent == "ABC123"

    def test_update_patent_raises_on_conflict_with_another_vehicle(self, vehicle, db):
        Vehicle.objects.create(patent="ZZZ999", brand="BMW", model="X1", year=2020)
        with pytest.raises(VehiclePatentAlreadyExists):
            VehicleService.update(vehicle.pk, patent="ZZZ999")

    def test_update_raises_not_found(self):
        with pytest.raises(VehicleNotFound):
            VehicleService.update(999, brand="Ghost")

    # --- delete ---

    def test_delete_removes_vehicle(self, vehicle):
        VehicleService.delete(vehicle.pk)
        assert not Vehicle.objects.filter(pk=vehicle.pk).exists()

    def test_delete_raises_not_found(self):
        with pytest.raises(VehicleNotFound):
            VehicleService.delete(999)


# ---------------------------------------------------------------------------
# VehicleLogService
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestVehicleLogService:
    # --- get_by_id ---

    def test_get_by_id_returns_log(self, vehicle, vehicle_log):
        result = VehicleLogService.get_by_id(vehicle.pk, vehicle_log.pk)
        assert result == vehicle_log

    def test_get_by_id_raises_not_found_for_wrong_vehicle(self, vehicle_log, db):
        other_vehicle = Vehicle.objects.create(
            patent="OTH000", brand="X", model="Y", year=2020
        )
        with pytest.raises(VehicleLogNotFound) as exc_info:
            VehicleLogService.get_by_id(other_vehicle.pk, vehicle_log.pk)
        assert exc_info.value.status_code == 404

    def test_get_by_id_raises_not_found_for_missing_log(self, vehicle):
        with pytest.raises(VehicleLogNotFound):
            VehicleLogService.get_by_id(vehicle.pk, 999)

    # --- list_by_vehicle ---

    def test_list_by_vehicle_returns_logs(self, vehicle, vehicle_log):
        result = VehicleLogService.list_by_vehicle(vehicle.pk)
        assert vehicle_log in result

    def test_list_by_vehicle_raises_not_found_for_missing_vehicle(self):
        with pytest.raises(VehicleNotFound):
            VehicleLogService.list_by_vehicle(999)

    def test_list_by_vehicle_returns_only_own_logs(self, vehicle, vehicle_log, db):
        other = Vehicle.objects.create(patent="OTH111", brand="X", model="Y", year=2020)
        VehicleLog.objects.create(vehicle=other, title="Other log", detail="detail")

        result = VehicleLogService.list_by_vehicle(vehicle.pk)
        assert all(log.vehicle_id == vehicle.pk for log in result)

    # --- create ---

    def test_create_returns_vehicle_log(self, vehicle, user):
        log = VehicleLogService.create(
            vehicle.pk,
            title="Service check",
            detail="Oil changed.",
            created_by=user,
        )
        assert log.pk is not None
        assert log.vehicle == vehicle
        assert log.created_by == user

    def test_create_strips_whitespace(self, vehicle):
        log = VehicleLogService.create(
            vehicle.pk,
            title="  Inspection  ",
            detail="  All good.  ",
        )
        assert log.title == "Inspection"
        assert log.detail == "All good."

    def test_create_raises_not_found_for_missing_vehicle(self):
        with pytest.raises(VehicleNotFound):
            VehicleLogService.create(999, title="T", detail="D")

    def test_create_with_files_creates_media(self, vehicle):
        files = [
            make_uploaded_file("photo.jpg"),
            make_uploaded_file("clip.mp4"),
        ]
        log = VehicleLogService.create(vehicle.pk, title="T", detail="D", files=files)
        assert log.media_files.count() == 2

    def test_create_with_invalid_file_rolls_back_log(self, vehicle):
        files = [make_uploaded_file("document.pdf")]
        with pytest.raises(InvalidMediaType):
            VehicleLogService.create(vehicle.pk, title="T", detail="D", files=files)

        assert VehicleLog.objects.filter(vehicle=vehicle).count() == 0

    # --- update ---

    def test_update_title(self, vehicle, vehicle_log):
        updated = VehicleLogService.update(
            vehicle.pk, vehicle_log.pk, title="Updated title"
        )
        assert updated.title == "Updated title"

    def test_update_detail(self, vehicle, vehicle_log):
        updated = VehicleLogService.update(
            vehicle.pk, vehicle_log.pk, detail="New detail."
        )
        assert updated.detail == "New detail."

    def test_update_raises_not_found(self, vehicle):
        with pytest.raises(VehicleLogNotFound):
            VehicleLogService.update(vehicle.pk, 999, title="X")

    # --- delete ---

    def test_delete_removes_log(self, vehicle, vehicle_log):
        VehicleLogService.delete(vehicle.pk, vehicle_log.pk)
        assert not VehicleLog.objects.filter(pk=vehicle_log.pk).exists()

    def test_delete_raises_not_found(self, vehicle):
        with pytest.raises(VehicleLogNotFound):
            VehicleLogService.delete(vehicle.pk, 999)


# ---------------------------------------------------------------------------
# MediaService
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMediaService:
    # --- get_by_id ---

    def test_get_by_id_returns_media(self, media):
        result = MediaService.get_by_id(media.pk)
        assert result == media

    def test_get_by_id_raises_not_found(self):
        with pytest.raises(MediaNotFound) as exc_info:
            MediaService.get_by_id(999)
        assert exc_info.value.status_code == 404

    # --- list_by_log ---

    def test_list_by_log_returns_media(self, vehicle, vehicle_log, media):
        result = MediaService.list_by_log(vehicle.pk, vehicle_log.pk)
        assert media in result

    def test_list_by_log_raises_not_found_for_wrong_log(self, vehicle):
        with pytest.raises(VehicleLogNotFound):
            MediaService.list_by_log(vehicle.pk, 999)

    # --- _resolve_type ---

    @pytest.mark.parametrize(
        "filename,expected_type",
        [
            ("photo.jpg", Media.MediaType.PHOTO),
            ("photo.jpeg", Media.MediaType.PHOTO),
            ("image.png", Media.MediaType.PHOTO),
            ("image.webp", Media.MediaType.PHOTO),
            ("clip.mp4", Media.MediaType.VIDEO),
            ("clip.mov", Media.MediaType.VIDEO),
            ("clip.avi", Media.MediaType.VIDEO),
        ],
    )
    def test_resolve_type_valid_extensions(self, filename, expected_type):
        file = make_uploaded_file(filename)
        assert MediaService._resolve_type(file) == expected_type

    @pytest.mark.parametrize(
        "filename", ["report.pdf", "data.csv", "archive.zip", "noextension"]
    )
    def test_resolve_type_invalid_extension_raises(self, filename):
        file = make_uploaded_file(filename)
        with pytest.raises(InvalidMediaType) as exc_info:
            MediaService._resolve_type(file)
        assert exc_info.value.status_code == 422

    # --- create ---

    def test_create_photo(self, vehicle_log):
        file = make_uploaded_file("front.jpg")
        media = MediaService.create(vehicle_log.pk, file=file)
        assert media.pk is not None
        assert media.type == Media.MediaType.PHOTO

    def test_create_video(self, vehicle_log):
        file = make_uploaded_file("drive.mp4")
        media = MediaService.create(vehicle_log.pk, file=file)
        assert media.type == Media.MediaType.VIDEO

    def test_create_raises_on_invalid_type(self, vehicle_log):
        file = make_uploaded_file("doc.pdf")
        with pytest.raises(InvalidMediaType):
            MediaService.create(vehicle_log.pk, file=file)

    # --- bulk_create ---

    def test_bulk_create_returns_all_media(self, vehicle_log):
        files = [make_uploaded_file("a.jpg"), make_uploaded_file("b.png")]
        result = MediaService.bulk_create(vehicle_log.pk, files=files)
        assert len(result) == 2
        assert all(m.type == Media.MediaType.PHOTO for m in result)

    def test_bulk_create_rolls_back_on_invalid_file(self, vehicle_log):
        files = [make_uploaded_file("valid.jpg"), make_uploaded_file("bad.pdf")]
        with pytest.raises(InvalidMediaType):
            MediaService.bulk_create(vehicle_log.pk, files=files)

        assert Media.objects.filter(vehicle_log=vehicle_log).count() == 0

    # --- delete ---

    def test_delete_removes_db_record(self, media):
        media_id = media.pk
        with patch.object(media.file, "delete"):
            # Re-fetch so the mock on the instance isn't lost
            with patch("django.db.models.fields.files.FieldFile.delete"):
                MediaService.delete(media_id)
        assert not Media.objects.filter(pk=media_id).exists()

    def test_delete_raises_not_found(self):
        with pytest.raises(MediaNotFound):
            MediaService.delete(999)
