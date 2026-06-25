from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.vehicles.choices import VehicleLogStatus, VehicleLogType
from apps.vehicles.vehicle.domain.models import Media, Vehicle, VehicleLog

User = get_user_model()


# ===========================================================================
# Shared nested serializers
# ===========================================================================


class UserSummarySerializer(serializers.ModelSerializer):
    """Minimal user representation for nested read contexts."""

    class Meta:
        model = User
        fields = ("id", "email")


# ===========================================================================
# Media
# ===========================================================================


class MediaWriteSerializer(serializers.Serializer):
    """Validates a single file upload before handing it off to MediaService."""

    file = serializers.FileField()

    ALLOWED_EXTENSIONS = {
        "jpg",
        "jpeg",
        "png",
        "webp",  # photos
        "mp4",
        "mov",
        "avi",  # videos
    }

    def validate_file(self, value):
        ext = value.name.rsplit(".", 1)[-1].lower() if "." in value.name else ""
        if ext not in self.ALLOWED_EXTENSIONS:
            raise serializers.ValidationError(
                f"'{ext}' is not a supported file type. "
                f"Allowed: {', '.join(sorted(self.ALLOWED_EXTENSIONS))}."
            )
        return value


class MediaDetailSerializer(serializers.ModelSerializer):
    """Full representation of a media file (single-resource responses)."""

    type_display = serializers.CharField(source="get_type_display", read_only=True)

    class Meta:
        model = Media
        fields = ("id", "file", "type", "type_display", "vehicle_log_id")
        read_only_fields = fields


class MediaListSerializer(serializers.ModelSerializer):
    """Compact representation used inside log list responses."""

    class Meta:
        model = Media
        fields = ("id", "file", "type")
        read_only_fields = fields


# ===========================================================================
# VehicleLog
# ===========================================================================


class VehicleLogWriteSerializer(serializers.Serializer):
    """Validates creation and update payloads for VehicleLog."""

    title = serializers.CharField(max_length=255)
    detail = serializers.CharField()
    files = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        allow_empty=True,
    )
    type = serializers.ChoiceField(choices=VehicleLogType.choices)
    status = serializers.ChoiceField(choices=VehicleLogStatus.choices)

    def validate_files(self, values):
        allowed = {"jpg", "jpeg", "png", "webp", "mp4", "mov", "avi"}
        for file in values:
            ext = file.name.rsplit(".", 1)[-1].lower() if "." in file.name else ""
            if ext not in allowed:
                raise serializers.ValidationError(
                    f"'{file.name}' has an unsupported extension '{ext}'."
                )
        return values


class VehicleLogUpdateSerializer(serializers.Serializer):
    """Partial update: at least one field is required."""

    title = serializers.CharField(max_length=255, required=False)
    detail = serializers.CharField(required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "At least one field (title, detail) must be provided."
            )
        return attrs


class VehicleLogDetailSerializer(serializers.ModelSerializer):
    """Full representation of a log including nested user and all media."""

    created_by = UserSummarySerializer(read_only=True)
    media_files = MediaDetailSerializer(many=True, read_only=True)

    class Meta:
        model = VehicleLog
        fields = (
            "id",
            "vehicle_id",
            "title",
            "detail",
            "created_by",
            "created_at",
            "media_files",
            "type",
            "status",
        )
        read_only_fields = fields


class VehicleLogListSerializer(serializers.ModelSerializer):
    """Compact representation for log list — omits detail text and nested media."""

    created_by = UserSummarySerializer(read_only=True)
    media_count = serializers.IntegerField(
        source="media_files.count",
        read_only=True,
    )

    class Meta:
        model = VehicleLog
        fields = (
            "id",
            "title",
            "created_by",
            "created_at",
            "media_count",
            "type",
            "status",
        )
        read_only_fields = fields


# ===========================================================================
# Vehicle
# ===========================================================================


class VehicleWriteSerializer(serializers.Serializer):
    """Validates creation and full-update payloads for Vehicle."""

    patent = serializers.CharField(max_length=10)
    brand = serializers.CharField(max_length=100)
    model = serializers.CharField(max_length=100)
    year = serializers.IntegerField(min_value=1886, max_value=2100)

    def validate_patent(self, value: str) -> str:
        return value.upper().strip()


class VehicleUpdateSerializer(serializers.Serializer):
    """Partial update: at least one field is required."""

    patent = serializers.CharField(max_length=10, required=False)
    brand = serializers.CharField(max_length=100, required=False)
    model = serializers.CharField(max_length=100, required=False)
    year = serializers.IntegerField(min_value=1886, max_value=2100, required=False)

    def validate_patent(self, value: str) -> str:
        return value.upper().strip()

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "At least one field (patent, brand, model, year) must be provided."
            )
        return attrs


class VehicleDetailSerializer(serializers.ModelSerializer):
    """Full representation of a vehicle including all its logs."""

    logs = VehicleLogListSerializer(many=True, read_only=True)

    class Meta:
        model = Vehicle
        fields = ("id", "patent", "brand", "model", "year", "created_at", "logs")
        read_only_fields = fields


class VehicleListSerializer(serializers.ModelSerializer):
    """Compact representation for vehicle list — no nested logs."""

    log_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Vehicle
        fields = ("id", "patent", "brand", "model", "year", "created_at", "log_count")
        read_only_fields = fields


class VehicleLogStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=VehicleLogStatus.choices)


class DashboardSummarySerializer(serializers.Serializer):
    total_vehicles = serializers.IntegerField()
    total_logs = serializers.IntegerField()
    logs_today = serializers.IntegerField()
    logs_this_week = serializers.IntegerField()
    logs_this_month = serializers.IntegerField()
    pending_logs = serializers.IntegerField()
    pending_incidents = serializers.IntegerField()


class LogsByStatusSerializer(serializers.Serializer):
    status = serializers.CharField()
    label = serializers.CharField()
    count = serializers.IntegerField()


class LogsByTypeSerializer(serializers.Serializer):
    type = serializers.CharField()
    label = serializers.CharField()
    count = serializers.IntegerField()


class LogsByTypeAndStatusSerializer(serializers.Serializer):
    type = serializers.CharField()
    label = serializers.CharField()
    statuses = serializers.DictField(child=serializers.IntegerField())


class TopVehicleSerializer(serializers.Serializer):
    vehicle_id = serializers.IntegerField(source="id")
    patent = serializers.CharField()
    brand = serializers.CharField()
    model = serializers.CharField()
    log_count = serializers.IntegerField()


class TopUserSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(source="id")
    email = serializers.CharField()
    full_name = serializers.CharField()
    log_count = serializers.IntegerField()


class RecentLogVehicleSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    patent = serializers.CharField()


class RecentLogUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.CharField()


class RecentLogSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    type = serializers.CharField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    vehicle = RecentLogVehicleSerializer()
    created_by = RecentLogUserSerializer(allow_null=True)
    media_count = serializers.IntegerField()


class MediaSummarySerializer(serializers.Serializer):
    total_media = serializers.IntegerField()
    photos = serializers.IntegerField()
    videos = serializers.IntegerField()
    logs_without_media = serializers.IntegerField()


# --- Serializer raíz ---


class DashboardSerializer(serializers.Serializer):
    summary = DashboardSummarySerializer()
    logs_by_status = LogsByStatusSerializer(many=True)
    logs_by_type = LogsByTypeSerializer(many=True)
    logs_by_type_and_status = LogsByTypeAndStatusSerializer(many=True)
    top_vehicles_by_logs = TopVehicleSerializer(many=True)
    top_users_by_logs = TopUserSerializer(many=True)
    recent_logs = RecentLogSerializer(many=True)
    media_summary = MediaSummarySerializer()


class DashboardQuerySerializer(serializers.Serializer):
    date_from = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Fecha de inicio (inclusive). Formato YYYY-MM-DD.",
    )
    date_to = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Fecha de término (inclusive). Formato YYYY-MM-DD.",
    )

    def validate(self, attrs):
        date_from = attrs.get("date_from")
        date_to = attrs.get("date_to")

        if date_from and date_to and date_from > date_to:
            raise serializers.ValidationError(
                {"date_to": "'date_to' cannot be earlier than 'date_from'."}
            )

        return attrs
