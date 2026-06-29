from __future__ import annotations

from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from apps.vehicles.choices import VehicleLogStatus, VehicleLogType
from apps.vehicles.vehicle.domain.models import Media, Vehicle, VehicleLog

User = get_user_model()


# ===========================================================================
# Shared nested serializers
# ===========================================================================


class UserSummarySerializer(serializers.ModelSerializer):
    """
    Minimal user representation for nested read contexts.

    Used wherever a related user needs to be displayed without exposing
    the full user payload (e.g. as the "created_by" or "assigned_to"
    reference inside a VehicleLog or VehicleAssignment response).
    """

    class Meta:
        model = User
        fields = ("id", "email")
        extra_kwargs = {
            "id": {"help_text": _("Unique identifier of the user.")},
            "email": {"help_text": _("Email address of the user.")},
        }


# ===========================================================================
# Media
# ===========================================================================


class MediaWriteSerializer(serializers.Serializer):
    """
    Validates a single file upload before handing it off to MediaService.

    This serializer is write-only and is not tied to the Media model: it
    exists purely to validate the incoming file (extension whitelist) prior
    to MediaService creating the actual Media instance and assigning its
    `type` based on the detected extension.
    """

    file = serializers.FileField(
        help_text=(
            _(
                "File to upload. Must be an image (jpg, jpeg, png, webp) or a video (mp4, mov, avi). The file type is inferred from its extension."
            )
        )
    )

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
        """
        Reject files whose extension is not in ALLOWED_EXTENSIONS.

        The extension is extracted from the filename rather than the
        content type, since browsers/clients do not always send a
        reliable MIME type for mobile uploads.
        """
        ext = value.name.rsplit(".", 1)[-1].lower() if "." in value.name else ""
        if ext not in self.ALLOWED_EXTENSIONS:
            raise serializers.ValidationError(
                f"'{ext}' is not a supported file type. "
                f"Allowed: {', '.join(sorted(self.ALLOWED_EXTENSIONS))}."
            )
        return value


class MediaDetailSerializer(serializers.ModelSerializer):
    """
    Full representation of a media file (single-resource responses).

    Used when a Media instance is retrieved or returned on its own
    (e.g. GET /media/{id}/), as opposed to being nested inside a
    VehicleLog list, where MediaListSerializer is used instead.
    """

    type_display = serializers.CharField(
        source="get_type_display",
        read_only=True,
        help_text=_("Human-readable label for the media type (e.g. 'Photo', 'Video')."),
    )

    class Meta:
        model = Media
        fields = ("id", "file", "type", "type_display", "vehicle_log_id")
        read_only_fields = fields
        extra_kwargs = {
            "id": {"help_text": _("Unique identifier of the media file.")},
            "file": {"help_text": "URL of the stored file."},
            "type": {
                "help_text": _(
                    "Media type code, inferred from the file extension at upload time."
                )
            },
            "vehicle_log_id": {
                "help_text": _("ID of the vehicle log this media file is attached to.")
            },
        }


class MediaListSerializer(serializers.ModelSerializer):
    """
    Compact representation used inside log list responses.

    Intentionally excludes `vehicle_log_id` and `type_display`, since
    list responses already nest this serializer under the parent log
    and don't need the redundant FK or the display label.
    """

    class Meta:
        model = Media
        fields = ("id", "file", "type")
        read_only_fields = fields
        extra_kwargs = {
            "id": {"help_text": _("Unique identifier of the media file.")},
            "file": {"help_text": _("URL of the stored file.")},
            "type": {"help_text": _("Media type code (e.g. photo or video).")},
        }


# ===========================================================================
# VehicleLog
# ===========================================================================


class VehicleLogWriteSerializer(serializers.Serializer):
    """
    Validates creation and update payloads for VehicleLog.

    Used for both create (POST) and full update (PUT) operations. File
    validation mirrors MediaWriteSerializer's extension whitelist, but is
    duplicated here (rather than reused) since files arrive as part of a
    larger payload alongside the log's own fields.
    """

    title = serializers.CharField(
        max_length=255,
        help_text=_("Short title summarizing the log entry."),
    )
    detail = serializers.CharField(
        help_text=_(
            "Full description of the incident, observation, cleaning, or maintenance event."
        )
    )
    files = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        allow_empty=True,
        help_text=(
            _(
                "Optional list of files (photos and/or videos) to attach to this log. Accepted extensions: jpg, jpeg, png, webp, mp4, mov, avi."
            )
        ),
    )
    type = serializers.ChoiceField(
        choices=VehicleLogType.choices,
        help_text=_(
            "Category of the log entry (e.g. incident, observation, cleaning, maintenance)."
        ),
    )
    status = serializers.ChoiceField(
        choices=VehicleLogStatus.choices,
        help_text=_("Current status of the log entry."),
    )

    def validate_files(self, values):
        """
        Reject any uploaded file whose extension is not in the allowed set.

        Unlike MediaWriteSerializer, this validates a list of files rather
        than a single one, since a VehicleLog can be created with multiple
        attachments in one request.
        """
        allowed = {"jpg", "jpeg", "png", "webp", "mp4", "mov", "avi"}
        for file in values:
            ext = file.name.rsplit(".", 1)[-1].lower() if "." in file.name else ""
            if ext not in allowed:
                raise serializers.ValidationError(
                    f"'{file.name}' has an unsupported extension '{ext}'."
                )
        return values


class VehicleLogUpdateSerializer(serializers.Serializer):
    """
    Partial update: at least one field is required.

    Intended for PATCH requests where only `title` and/or `detail` can be
    amended after creation. `type`, `status`, and attached files are not
    editable through this serializer — status transitions and media
    management are handled through dedicated endpoints/actions.
    """

    title = serializers.CharField(
        max_length=255,
        required=False,
        help_text=_(
            "New title for the log entry. Optional, but at least one field is required."
        ),
    )
    detail = serializers.CharField(
        required=False,
        help_text=_(
            "New detail text for the log entry. Optional, but at least one field is required."
        ),
    )

    def validate(self, attrs):
        """Ensure the request isn't a no-op by requiring at least one field."""
        if not attrs:
            raise serializers.ValidationError(
                "At least one field (title, detail) must be provided."
            )
        return attrs


class VehicleLogDetailSerializer(serializers.ModelSerializer):
    """
    Full representation of a log including nested user and all media.

    Used for single-resource responses (e.g. GET /vehicle-logs/{id}/),
    where the full media payload and creator details are needed. For list
    views, see VehicleLogListSerializer, which omits both for performance.
    """

    created_by = UserSummarySerializer(
        read_only=True,
        help_text=_("User who created this log entry."),
    )
    media_files = MediaDetailSerializer(
        many=True,
        read_only=True,
        help_text=_("All media files (photos/videos) attached to this log entry."),
    )

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
        extra_kwargs = {
            "id": {"help_text": _("Unique identifier of the log entry.")},
            "vehicle_id": {
                "help_text": _("ID of the vehicle this log entry belongs to.")
            },
            "title": {"help_text": _("Short title summarizing the log entry.")},
            "detail": {
                "help_text": _(
                    "Full description of the incident, observation, cleaning, or maintenance event."
                )
            },
            "created_at": {"help_text": _("Timestamp when the log entry was created.")},
            "type": {
                "help_text": _(
                    "Category of the log entry (e.g. incident, observation, cleaning, maintenance)."
                )
            },
            "status": {"help_text": _("Current status of the log entry.")},
        }


class VehicleLogListSerializer(serializers.ModelSerializer):
    """
    Compact representation for log list — omits detail text and nested media.

    `media_count` is exposed instead of the full `media_files` list so that
    clients can show an attachment indicator (e.g. a paperclip icon with a
    number) without the cost of serializing every attached file.
    """

    created_by = UserSummarySerializer(
        read_only=True,
        help_text=_("User who created this log entry."),
    )
    media_count = serializers.IntegerField(
        source="media_files.count",
        read_only=True,
        help_text=_("Number of media files attached to this log entry."),
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
        extra_kwargs = {
            "id": {"help_text": _("Unique identifier of the log entry.")},
            "title": {"help_text": _("Short title summarizing the log entry.")},
            "created_at": {"help_text": _("Timestamp when the log entry was created.")},
            "type": {
                "help_text": _(
                    "Category of the log entry (e.g. incident, observation, cleaning, maintenance)."
                )
            },
            "status": {"help_text": _("Current status of the log entry.")},
        }


# ===========================================================================
# Vehicle
# ===========================================================================


class VehicleWriteSerializer(serializers.Serializer):
    """
    Validates creation and full-update payloads for Vehicle.

    Used for create (POST) and full update (PUT), where every field is
    required. For partial updates, see VehicleUpdateSerializer.
    """

    patent = serializers.CharField(
        max_length=10,
        help_text=_(
            "Vehicle license plate. Automatically uppercased and stripped of whitespace."
        ),
    )
    brand = serializers.CharField(
        max_length=100,
        help_text=_("Vehicle manufacturer (e.g. Toyota, Ford)."),
    )
    model = serializers.CharField(
        max_length=100,
        help_text=_("Vehicle model name (e.g. Hilux, Ranger)."),
    )
    year = serializers.IntegerField(
        min_value=1886,
        max_value=2100,
        help_text=_(
            "Manufacturing year of the vehicle. Must be between 1886 and 2100."
        ),
    )

    def validate_patent(self, value: str) -> str:
        """Normalize the plate to uppercase with no surrounding whitespace."""
        return value.upper().strip()


class VehicleUpdateSerializer(serializers.Serializer):
    """
    Partial update: at least one field is required.

    Intended for PATCH requests, where any subset of the vehicle's fields
    can be amended. All fields use the same validation rules as
    VehicleWriteSerializer, but none are required individually.
    """

    patent = serializers.CharField(
        max_length=10,
        required=False,
        help_text=_(
            "New license plate. Automatically uppercased and stripped of whitespace."
        ),
    )
    brand = serializers.CharField(
        max_length=100,
        required=False,
        help_text=_("New vehicle manufacturer."),
    )
    model = serializers.CharField(
        max_length=100,
        required=False,
        help_text=_("New vehicle model name."),
    )
    year = serializers.IntegerField(
        min_value=1886,
        max_value=2100,
        required=False,
        help_text=_("New manufacturing year. Must be between 1886 and 2100."),
    )

    def validate_patent(self, value: str) -> str:
        """Normalize the plate to uppercase with no surrounding whitespace."""
        return value.upper().strip()

    def validate(self, attrs):
        """Ensure the request isn't a no-op by requiring at least one field."""
        if not attrs:
            raise serializers.ValidationError(
                "At least one field (patent, brand, model, year) must be provided."
            )
        return attrs


class VehicleDetailSerializer(serializers.ModelSerializer):
    """
    Full representation of a vehicle including all its logs.

    Used for single-resource responses (e.g. GET /vehicles/{id}/). The
    nested `logs` field uses VehicleLogListSerializer (not the detail
    version) to keep the payload manageable when a vehicle has many logs.
    """

    logs = VehicleLogListSerializer(
        many=True,
        read_only=True,
        help_text=_(
            "All log entries (incidents, observations, cleanings, maintenance) registered for this vehicle."
        ),
    )

    class Meta:
        model = Vehicle
        fields = ("id", "patent", "brand", "model", "year", "created_at", "logs")
        read_only_fields = fields
        extra_kwargs = {
            "id": {"help_text": _("Unique identifier of the vehicle.")},
            "patent": {"help_text": _("Vehicle license plate.")},
            "brand": {"help_text": _("Vehicle manufacturer.")},
            "model": {"help_text": _("Vehicle model name.")},
            "year": {"help_text": _("Manufacturing year of the vehicle.")},
            "created_at": {
                "help_text": _("Timestamp when the vehicle was registered.")
            },
        }


class VehicleListSerializer(serializers.ModelSerializer):
    """
    Compact representation for vehicle list — no nested logs.

    `log_count` is expected to be provided via queryset annotation
    (e.g. `Count("logs", distinct=True)`) rather than a nested serializer,
    to avoid the cost of serializing every log for every vehicle in a list.
    """

    log_count = serializers.IntegerField(
        read_only=True,
        help_text=_("Total number of log entries registered for this vehicle."),
    )

    class Meta:
        model = Vehicle
        fields = ("id", "patent", "brand", "model", "year", "created_at", "log_count")
        read_only_fields = fields
        extra_kwargs = {
            "id": {"help_text": _("Unique identifier of the vehicle.")},
            "patent": {"help_text": _("Vehicle license plate.")},
            "brand": {"help_text": _("Vehicle manufacturer.")},
            "model": {"help_text": _("Vehicle model name.")},
            "year": {"help_text": _("Manufacturing year of the vehicle.")},
            "created_at": {
                "help_text": _("Timestamp when the vehicle was registered.")
            },
        }


class VehicleLogStatusSerializer(serializers.Serializer):
    """
    Validates a status-only payload for transitioning a VehicleLog's status.

    Used by dedicated status-change actions/endpoints where only the
    `status` field is editable, separate from VehicleLogUpdateSerializer
    (which only allows `title`/`detail`).
    """

    status = serializers.ChoiceField(
        choices=VehicleLogStatus.choices,
        help_text=_("New status to set for the log entry."),
    )


class DashboardSummarySerializer(serializers.Serializer):
    """
    Top-level counters shown on the dashboard's summary panel.

    `total_vehicles` and `total_logs` are live counters unaffected by the
    optional `date_from`/`date_to` query params, while the remaining
    time-bucketed and pending counts are computed relative to "now"
    (today, this week, this month) and are independent of those params too.
    """

    total_vehicles = serializers.IntegerField(
        help_text=_("Total number of registered vehicles, regardless of date filters.")
    )
    total_logs = serializers.IntegerField(
        help_text=_(
            "Total number of log entries ever created, regardless of date filters."
        )
    )
    logs_today = serializers.IntegerField(
        help_text=_("Number of log entries created today.")
    )
    logs_this_week = serializers.IntegerField(
        help_text=_("Number of log entries created during the current week.")
    )
    logs_this_month = serializers.IntegerField(
        help_text=_("Number of log entries created during the current month.")
    )
    pending_logs = serializers.IntegerField(
        help_text=_("Number of log entries currently in a pending status.")
    )
    pending_incidents = serializers.IntegerField(
        help_text=_(
            "Number of log entries of type incident currently in a pending status."
        )
    )


class LogsByStatusSerializer(serializers.Serializer):
    """
    Aggregated log count grouped by status, for dashboard charts.

    Subject to the optional `date_from`/`date_to` filters applied at the
    dashboard endpoint level.
    """

    status = serializers.CharField(
        help_text="Status code (e.g. 'pending', 'completed')."
    )
    label = serializers.CharField(help_text=_("Human-readable label for the status."))
    count = serializers.IntegerField(
        help_text=_("Number of log entries with this status.")
    )


class LogsByTypeSerializer(serializers.Serializer):
    """
    Aggregated log count grouped by type, for dashboard charts.

    Subject to the optional `date_from`/`date_to` filters applied at the
    dashboard endpoint level.
    """

    type = serializers.CharField(
        help_text="Log type code (e.g. 'incident', 'maintenance')."
    )
    label = serializers.CharField(help_text=_("Human-readable label for the log type."))
    count = serializers.IntegerField(help_text=_("Number of log entries of this type."))


class LogsByTypeAndStatusSerializer(serializers.Serializer):
    """
    Aggregated log count grouped by type, broken down further by status.

    Used for stacked/grouped chart visualizations where each log type
    needs a per-status breakdown (e.g. "incident" split into
    pending/completed/expired counts) rather than a single total.
    Subject to the optional `date_from`/`date_to` filters applied at the
    dashboard endpoint level.
    """

    type = serializers.CharField(
        help_text=_("Log type code (e.g. 'incident', 'maintenance').")
    )
    label = serializers.CharField(help_text=_("Human-readable label for the log type."))
    statuses = serializers.DictField(
        child=serializers.IntegerField(),
        help_text=_("Mapping of status code to log count for this type (e.g. {'pending': 3, 'completed': 7})."),
    )


class TopVehicleSerializer(serializers.Serializer):
    """
    Vehicle ranked by number of associated log entries, for dashboard rankings.

    Subject to the optional `date_from`/`date_to` filters applied at the
    dashboard endpoint level.
    """

    vehicle_id = serializers.IntegerField(
        source="id",
        help_text=_("Unique identifier of the vehicle."),
    )
    patent = serializers.CharField(help_text=_("Vehicle license plate."))
    brand = serializers.CharField(help_text=_("Vehicle manufacturer."))
    model = serializers.CharField(help_text=_("Vehicle model name."))
    log_count = serializers.IntegerField(
        help_text=_("Number of log entries registered for this vehicle.")
    )


class TopUserSerializer(serializers.Serializer):
    """
    User ranked by number of log entries they created, for dashboard rankings.

    Subject to the optional `date_from`/`date_to` filters applied at the
    dashboard endpoint level.
    """

    user_id = serializers.IntegerField(
        source="id",
        help_text=_("Unique identifier of the user."),
    )
    email = serializers.CharField(help_text=_("Email address of the user."))
    full_name = serializers.CharField(help_text=_("Full name of the user."))
    log_count = serializers.IntegerField(
        help_text=_("Number of log entries created by this user.")
    )


class RecentLogVehicleSerializer(serializers.Serializer):
    """Minimal vehicle reference nested inside RecentLogSerializer."""

    id = serializers.IntegerField(help_text=_("Unique identifier of the vehicle."))
    patent = serializers.CharField(help_text=_("Vehicle license plate."))


class RecentLogUserSerializer(serializers.Serializer):
    """Minimal user reference nested inside RecentLogSerializer."""

    id = serializers.IntegerField(help_text=_("Unique identifier of the user."))
    email = serializers.CharField(help_text=_("Email address of the user."))


class RecentLogSerializer(serializers.Serializer):
    """
    Compact representation of a recently created log entry, for the
    dashboard's activity feed.

    Uses its own minimal nested serializers (RecentLogVehicleSerializer,
    RecentLogUserSerializer) instead of UserSummarySerializer or
    VehicleListSerializer, since the dashboard only needs a couple of
    fields from each and is built from a separate, lighter query.
    """

    id = serializers.IntegerField(help_text=_("Unique identifier of the log entry."))
    title = serializers.CharField(help_text=_("Short title summarizing the log entry."))
    type = serializers.CharField(
        help_text=_("Category of the log entry (e.g. incident, observation, cleaning, maintenance).")
    )
    status = serializers.CharField(help_text=_("Current status of the log entry."))
    created_at = serializers.DateTimeField(
        help_text=_("Timestamp when the log entry was created.")
    )
    vehicle = RecentLogVehicleSerializer(help_text=_("Vehicle this log entry belongs to."))
    created_by = RecentLogUserSerializer(
        allow_null=True,
        help_text=_("User who created this log entry. Null if the creator no longer exists."),
    )
    media_count = serializers.IntegerField(
        help_text=_("Number of media files attached to this log entry.")
    )


class MediaSummarySerializer(serializers.Serializer):
    """
    Aggregated media counts for the dashboard's media panel.

    Subject to the optional `date_from`/`date_to` filters applied at the
    dashboard endpoint level.
    """

    total_media = serializers.IntegerField(
        help_text=_("Total number of media files (photos and videos) attached to log entries.")
    )
    photos = serializers.IntegerField(
        help_text=_("Number of photo files attached to log entries.")
    )
    videos = serializers.IntegerField(
        help_text=_("Number of video files attached to log entries.")
    )
    logs_without_media = serializers.IntegerField(
        help_text=_("Number of log entries that have no media files attached.")
    )


# --- Serializer raíz ---


class DashboardSerializer(serializers.Serializer):
    """
    Root serializer composing the full dashboard payload.

    Each section is built from a separate query in DashboardService and
    composed here purely for output shaping; this serializer performs no
    validation and is read-only by nature (used only as a response
    serializer, never to parse input).
    """

    summary = DashboardSummarySerializer(
        help_text=_("Top-level counters (vehicles, logs, pending items).")
    )
    logs_by_status = LogsByStatusSerializer(
        many=True,
        help_text=_("Log entry counts grouped by status, for chart visualizations."),
    )
    logs_by_type = LogsByTypeSerializer(
        many=True,
        help_text=_("Log entry counts grouped by type, for chart visualizations."),
    )
    logs_by_type_and_status = LogsByTypeAndStatusSerializer(
        many=True,
        help_text=_("Log entry counts grouped by type and further broken down by status."),
    )
    top_vehicles_by_logs = TopVehicleSerializer(
        many=True,
        help_text=_("Vehicles ranked by number of associated log entries."),
    )
    top_users_by_logs = TopUserSerializer(
        many=True,
        help_text=_("Users ranked by number of log entries they created."),
    )
    recent_logs = RecentLogSerializer(
        many=True,
        help_text=_("Most recently created log entries, for the activity feed."),
    )
    media_summary = MediaSummarySerializer(
        help_text=_("Aggregated counts of attached media (photos, videos, logs without media).")
    )


class DashboardQuerySerializer(serializers.Serializer):
    """
    Validates the optional date-range query params for the dashboard endpoint.

    Both params are optional; when omitted, the date-dependent sections of
    DashboardSerializer (e.g. logs_by_status, logs_by_type,
    top_vehicles_by_logs) fall back to an unfiltered range, while
    total_vehicles, total_logs, and the time-bucketed counters
    (logs_today/this_week/this_month) remain unaffected regardless.
    """

    date_from = serializers.DateField(
        required=False,
        allow_null=True,
        help_text=_("Start date (inclusive). Format YYYY-MM-DD."),
    )
    date_to = serializers.DateField(
        required=False,
        allow_null=True,
        help_text=_("End date (inclusive). Format YYYY-MM-DD."),
    )

    def validate(self, attrs):
        """Ensure date_to is not earlier than date_from when both are provided."""
        date_from = attrs.get("date_from")
        date_to = attrs.get("date_to")

        if date_from and date_to and date_from > date_to:
            raise serializers.ValidationError(
                {"date_to": "'date_to' cannot be earlier than 'date_from'."}
            )

        return attrs
