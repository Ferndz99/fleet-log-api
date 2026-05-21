"""
Tests for Vehicle, VehicleLog and Media models.

Run with:
    pytest apps/<your_app>/tests/test_models.py -v
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.vehicles.vehicle.domain.models import Media, Vehicle, VehicleLog

User = get_user_model()

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    return User.objects.create_user(email="testuser@example.com", password="secret")


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
        detail="No visible damage found on the bodywork.",
    )


@pytest.fixture
def media(vehicle_log):
    return Media.objects.create(
        vehicle_log=vehicle_log,
        file="vehicle_logs/2024/01/01/front.jpg",
        type=Media.MediaType.PHOTO,
    )


# ---------------------------------------------------------------------------
# Vehicle
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestVehicleModel:
    def test_create_vehicle(self, vehicle):
        assert vehicle.pk is not None
        assert vehicle.patent == "ABC123"
        assert vehicle.brand == "Toyota"
        assert vehicle.model == "Corolla"
        assert vehicle.year == 2022
        assert vehicle.created_at is not None

    def test_str_representation(self, vehicle):
        assert str(vehicle) == "Toyota Corolla (2022) — ABC123"

    def test_patent_is_unique(self, vehicle):
        with pytest.raises(IntegrityError):
            Vehicle.objects.create(
                patent="ABC123",  # duplicate
                brand="Honda",
                model="Civic",
                year=2021,
            )

    def test_ordering_is_newest_first(self, db):
        v1 = Vehicle.objects.create(
            patent="AAA001", brand="Ford", model="Focus", year=2020
        )
        v2 = Vehicle.objects.create(
            patent="BBB002", brand="Kia", model="Rio", year=2021
        )

        patents = list(Vehicle.objects.values_list("patent", flat=True))
        assert patents.index("BBB002") < patents.index("AAA001")

    def test_logs_reverse_relation(self, vehicle, vehicle_log):
        assert vehicle.logs.count() == 1
        assert vehicle.logs.first() == vehicle_log


# ---------------------------------------------------------------------------
# VehicleLog
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestVehicleLogModel:
    def test_create_vehicle_log(self, vehicle_log, vehicle, user):
        assert vehicle_log.pk is not None
        assert vehicle_log.vehicle == vehicle
        assert vehicle_log.created_by == user
        assert vehicle_log.title == "Initial inspection"
        assert vehicle_log.created_at is not None

    def test_str_representation(self, vehicle_log):
        assert str(vehicle_log) == "[ABC123] Initial inspection"

    def test_created_by_set_null_on_user_delete(self, vehicle_log, user):
        user.delete()
        vehicle_log.refresh_from_db()
        assert vehicle_log.created_by is None

    def test_cascade_delete_with_vehicle(self, vehicle, vehicle_log):
        log_id = vehicle_log.pk
        vehicle.delete()
        assert not VehicleLog.objects.filter(pk=log_id).exists()

    def test_vehicle_log_without_user(self, vehicle):
        log = VehicleLog.objects.create(
            vehicle=vehicle,
            created_by=None,
            title="Anonymous log",
            detail="Created without an assigned user.",
        )
        assert log.created_by is None

    def test_media_files_reverse_relation(self, vehicle_log, media):
        assert vehicle_log.media_files.count() == 1
        assert vehicle_log.media_files.first() == media


# ---------------------------------------------------------------------------
# Media
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMediaModel:
    def test_create_photo(self, media):
        assert media.pk is not None
        assert media.type == Media.MediaType.PHOTO
        assert media.file.name == "vehicle_logs/2024/01/01/front.jpg"

    def test_create_video(self, vehicle_log):
        video = Media.objects.create(
            vehicle_log=vehicle_log,
            file="vehicle_logs/2024/01/01/clip.mp4",
            type=Media.MediaType.VIDEO,
        )
        assert video.type == Media.MediaType.VIDEO

    def test_str_representation_photo(self, media):
        assert str(media) == f"Photo — Log #{media.vehicle_log_id}"

    def test_str_representation_video(self, vehicle_log):
        video = Media.objects.create(
            vehicle_log=vehicle_log,
            file="vehicle_logs/2024/01/01/clip.mp4",
            type=Media.MediaType.VIDEO,
        )
        assert str(video) == f"Video — Log #{vehicle_log.pk}"

    def test_cascade_delete_with_vehicle_log(self, vehicle_log, media):
        media_id = media.pk
        vehicle_log.delete()
        assert not Media.objects.filter(pk=media_id).exists()

    def test_invalid_media_type_raises_on_full_clean(self, vehicle_log):
        media = Media(
            vehicle_log=vehicle_log,
            file="vehicle_logs/2024/01/01/doc.pdf",
            type="document",  # not a valid choice
        )
        with pytest.raises(ValidationError):
            media.full_clean()

    def test_multiple_media_per_log(self, vehicle_log):
        Media.objects.create(
            vehicle_log=vehicle_log,
            file="vehicle_logs/2024/01/01/front.jpg",
            type=Media.MediaType.PHOTO,
        )
        Media.objects.create(
            vehicle_log=vehicle_log,
            file="vehicle_logs/2024/01/01/rear.jpg",
            type=Media.MediaType.PHOTO,
        )
        assert vehicle_log.media_files.count() == 2
