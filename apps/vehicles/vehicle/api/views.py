from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
)
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter

from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from drf_spectacular.types import OpenApiTypes

from apps.vehicles.vehicle.api.filters import VehicleFilter
from apps.vehicles.vehicle.api.serializers import (
    DashboardQuerySerializer,
    DashboardSerializer,
    MediaDetailSerializer,
    MediaListSerializer,
    MediaWriteSerializer,
    VehicleDetailSerializer,
    VehicleListSerializer,
    VehicleLogDetailSerializer,
    VehicleLogListSerializer,
    VehicleLogStatusSerializer,
    VehicleLogUpdateSerializer,
    VehicleLogWriteSerializer,
    VehicleUpdateSerializer,
    VehicleWriteSerializer,
)
from apps.vehicles.vehicle.application.permissions import (
    MediaPermissions,
    VehicleLogPermissions,
    VehiclePermission,
)
from apps.vehicles.vehicle.domain.exceptions import VehiclePatentQueryParamRequired
from apps.vehicles.vehicle.domain.models import Vehicle, VehicleLog
from apps.vehicles.vehicle.domain.services import (
    DashboardService,
    MediaService,
    VehicleLogService,
    VehicleService,
)

from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Count
from rest_framework.views import APIView

from rest_framework.exceptions import ValidationError


from apps.common.api.serializers import ProblemDetailsSerializer
# ---------------------------------------------------------------------------
# VehicleViewSet
# ---------------------------------------------------------------------------


_SEARCH_PARAM = OpenApiParameter(
    name="search",
    type=str,
    location=OpenApiParameter.QUERY,
    description=(
        "**ES**: Búsqueda de texto libre. Aplica sobre **patent**, **brand** y **model**. "
        "Ejemplo: `search=Toyota`\n\n"
        "**EN**: Free-text search. Applied across **patent**, **brand**, and **model**. "
        "Example: `search=Toyota`"
    ),
)

_ORDERING_PARAM = OpenApiParameter(
    name="ordering",
    type=str,
    location=OpenApiParameter.QUERY,
    description=(
        "**ES**: Campo por el que ordenar los resultados. "
        "Prefija con `-` para orden descendente. "
        "Valores permitidos: `patent`, `brand`, `model`, `year`, `log_count`, `created_at`. "
        "Ejemplo: `ordering=-year`\n\n"
        "**EN**: Field to order results by. "
        "Prefix with `-` for descending order. "
        "Allowed values: `patent`, `brand`, `model`, `year`, `log_count`, `created_at`. "
        "Example: `ordering=-year`"
    ),
)

_FILTER_PARAMS = [
    OpenApiParameter(
        "brand",
        str,
        OpenApiParameter.QUERY,
        description="**ES**: Filtrar por marca (insensible a mayúsculas). Ej: `brand=Ford`\n\n"
        "**EN**: Filter by brand (case-insensitive). E.g. `brand=Ford`",
    ),
    OpenApiParameter(
        "model",
        str,
        OpenApiParameter.QUERY,
        description="**ES**: Filtrar por modelo (insensible a mayúsculas). Ej: `model=Ranger`\n\n"
        "**EN**: Filter by model (case-insensitive). E.g. `model=Ranger`",
    ),
    OpenApiParameter(
        "is_active",
        bool,
        OpenApiParameter.QUERY,
        description="**ES**: Estado del vehículo. `true` = activos, `false` = inactivos.\n\n"
        "**EN**: Vehicle status. `true` = active, `false` = inactive.",
    ),
    OpenApiParameter(
        "year_min",
        int,
        OpenApiParameter.QUERY,
        description="**ES**: Año de fabricación mínimo (inclusivo). Ej: `year_min=2018`\n\n"
        "**EN**: Minimum manufacturing year (inclusive). E.g. `year_min=2018`",
    ),
    OpenApiParameter(
        "year_max",
        int,
        OpenApiParameter.QUERY,
        description="**ES**: Año de fabricación máximo (inclusivo). Ej: `year_max=2023`\n\n"
        "**EN**: Maximum manufacturing year (inclusive). E.g. `year_max=2023`",
    ),
    OpenApiParameter(
        "min_logs",
        int,
        OpenApiParameter.QUERY,
        description="**ES**: Cantidad mínima de logs asociados.\n\n"
        "**EN**: Minimum number of associated logs.",
    ),
    OpenApiParameter(
        "max_logs",
        int,
        OpenApiParameter.QUERY,
        description="**ES**: Cantidad máxima de logs asociados.\n\n"
        "**EN**: Maximum number of associated logs.",
    ),
]


# Agregar este parámetro junto a los otros _PARAMS al inicio del archivo
_PATENT_PARAM = OpenApiParameter(
    name="patent",
    location=OpenApiParameter.QUERY,
    description="**ES**: Patente del vehículo a buscar (coincidencia exacta, insensible a mayúsculas).\n\n"
    "**EN**: Vehicle patent plate to search for (exact match, case-insensitive).",
    required=True,
    type=str,
)


_DATE_FROM_PARAM = OpenApiParameter(
    name="date_from",
    type=str,
    location=OpenApiParameter.QUERY,
    required=False,
    description="**ES**: Fecha de inicio (inclusive) para filtrar el dashboard. Formato ISO 8601. Ej: `2026-06-01`\n\n"
    "**EN**: Start date (inclusive) to filter the dashboard. ISO 8601 format. E.g. `2026-06-01`",
)

_DATE_TO_PARAM = OpenApiParameter(
    name="date_to",
    type=str,
    location=OpenApiParameter.QUERY,
    required=False,
    description="**ES**: Fecha de término (inclusive) para filtrar el dashboard. Formato ISO 8601. Ej: `2026-06-22`\n\n"
    "**EN**: End date (inclusive) to filter the dashboard. ISO 8601 format. E.g. `2026-06-22`",
)


@extend_schema_view(
    list=extend_schema(
        tags=["Vehicles"],
        summary="List vehicles",
        description=(
            "Returns a compact list of all registered vehicles including their log count. "
            "Supports **free-text search** (`search`), **field filtering** (`brand`, `model`, "
            "`year_min`, `year_max`, `min_logs`, `max_logs`) "
            "and **ordering** (`ordering`)."
        ),
        parameters=[_SEARCH_PARAM, _ORDERING_PARAM, *_FILTER_PARAMS],
        responses={
            200: VehicleListSerializer(many=True),
        },
    ),
    retrieve=extend_schema(
        tags=["Vehicles"],
        summary="Retrieve vehicle",
        description="Retrieve the full representation of a vehicle including its log list.",
        responses={
            200: VehicleDetailSerializer,
            404: OpenApiResponse(
                description="Vehicle not found", response=ProblemDetailsSerializer
            ),
        },
    ),
    create=extend_schema(
        tags=["Vehicles"],
        summary="Create vehicle",
        description="Register a new vehicle in the system.",
        request=VehicleWriteSerializer,
        responses={
            201: VehicleDetailSerializer,
            400: OpenApiResponse(
                description="Validation error", response=ProblemDetailsSerializer
            ),
            409: OpenApiResponse(
                description="A vehicle with this patent already exists",
                response=ProblemDetailsSerializer,
            ),
        },
    ),
    partial_update=extend_schema(
        tags=["Vehicles"],
        summary="Partially update vehicle",
        description="Update one or more fields of an existing vehicle. At least one field is required.",
        request=VehicleUpdateSerializer,
        responses={
            200: VehicleDetailSerializer,
            400: OpenApiResponse(
                description="Validation error", response=ProblemDetailsSerializer
            ),
            404: OpenApiResponse(
                description="Vehicle not found", response=ProblemDetailsSerializer
            ),
            409: OpenApiResponse(
                description="Patent already in use by another vehicle",
                response=ProblemDetailsSerializer,
            ),
        },
    ),
    destroy=extend_schema(
        tags=["Vehicles"],
        summary="Delete vehicle",
        description="Permanently delete a vehicle along with all its logs and media files.",
        responses={
            204: OpenApiResponse(description="Vehicle deleted successfully"),
            404: OpenApiResponse(
                description="Vehicle not found", response=ProblemDetailsSerializer
            ),
        },
    ),
    by_patent=extend_schema(
        tags=["Vehicles"],
        summary="Find vehicle by patent",
        description=(
            "Returns the full representation of a vehicle looked up by its patent plate. "
            "The search is **case-insensitive** and requires an exact match. "
            "Returns `404` if no vehicle with the given patent exists."
        ),
        parameters=[_PATENT_PARAM],
        responses={
            200: VehicleDetailSerializer,
            400: OpenApiResponse(
                description="Missing required 'patent' query parameter",
                response=ProblemDetailsSerializer,
            ),
            404: OpenApiResponse(
                description="Vehicle not found", response=ProblemDetailsSerializer
            ),
        },
    ),
)
class VehicleViewSet(
    GenericViewSet,
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    DestroyModelMixin,
):
    """
    Manages vehicle registration, retrieval, partial update, and deletion.

    Update intentionally only supports `partial_update` (PATCH), not full
    `update` (PUT): vehicles are expected to be amended field-by-field
    rather than fully replaced. List and retrieve use different
    serializers (`VehicleListSerializer` vs `VehicleDetailSerializer`)
    since the list view annotates a `log_count` instead of nesting the
    full log collection, which is only needed on the detail view.
    """

    serializer_class = VehicleListSerializer
    permission_classes = [VehiclePermission]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = VehicleFilter
    search_fields = ["patent", "brand", "model"]  # ?search=
    ordering_fields = ["patent", "brand", "model", "year", "log_count", "created_at"]
    ordering = ["patent"]

    serializer_class_by_action = {
        "create": VehicleWriteSerializer,
        "partial_update": VehicleUpdateSerializer,
        "list": VehicleListSerializer,
        "retrieve": VehicleDetailSerializer,
        "by_patent": VehicleDetailSerializer,
    }

    def get_queryset(self):  # type: ignore
        """Annotate each vehicle with its total log count for list/ordering/filtering."""
        return Vehicle.objects.annotate(log_count=Count("logs")).all()

    def get_object(self):  # type: ignore
        """Delegate object lookup to VehicleService instead of the default ORM lookup."""
        return VehicleService.get_by_id(self.kwargs["pk"])

    def get_serializer_class(self):
        """Return the serializer registered for the current action, falling back to the list serializer."""
        return self.serializer_class_by_action.get(self.action, self.serializer_class)

    def create(self, request, *args, **kwargs):
        """
        Validate the incoming payload, create the vehicle via the service
        layer, and return the full detail representation rather than the
        write serializer's own (write-only) representation.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        read_serializer = VehicleDetailSerializer(
            instance, context=self.get_serializer_context()
        )
        return Response(
            read_serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def perform_create(self, serializer):  # type: ignore
        """Delegate vehicle creation to VehicleService with the validated data."""
        return VehicleService.create(**serializer.validated_data)

    def partial_update(self, request, *args, **kwargs):
        """
        Validate the incoming partial payload, update the vehicle via the
        service layer, and return the full detail representation rather
        than the update serializer's own (write-only) representation.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = self.perform_update(serializer)

        read_serializer = VehicleDetailSerializer(
            instance, context=self.get_serializer_context()
        )
        return Response(read_serializer.data, status=status.HTTP_200_OK)

    def perform_update(self, serializer):  # type: ignore
        """Delegate vehicle update to VehicleService with the validated data."""
        return VehicleService.update(self.kwargs["pk"], **serializer.validated_data)

    def perform_destroy(self, instance):
        """Delegate vehicle deletion (cascading to logs and media) to VehicleService."""
        VehicleService.delete(instance.pk)

    @action(detail=False, methods=["get"], url_path="by-patent")
    def by_patent(self, request, *args, **kwargs):
        """
        Look up a single vehicle by its exact patent plate, passed as a
        required query parameter rather than a URL path segment, since
        patents are not used as the viewset's `lookup_field`.
        """
        patent = request.query_params.get("patent", "").strip()

        if not patent:
            raise VehiclePatentQueryParamRequired()

        instance = VehicleService.get_by_patent(patent)  # lanza Http404 si no existe
        serializer = VehicleDetailSerializer(
            instance, context=self.get_serializer_context()
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# VehicleLogViewSet
# ---------------------------------------------------------------------------


_VEHICLE_PK_PARAMETER = OpenApiParameter(
    name="vehicle_pk",
    type=OpenApiTypes.INT,
    location=OpenApiParameter.PATH,
    description="ID of the parent vehicle.",
)


@extend_schema_view(
    list=extend_schema(
        tags=["Vehicle Logs"],
        summary="List vehicle logs",
        description="Returns a compact list of all logs for a specific vehicle.",
        parameters=[_VEHICLE_PK_PARAMETER],
        responses={
            200: VehicleLogListSerializer(many=True),
            404: OpenApiResponse(
                response=ProblemDetailsSerializer, description="Vehicle not found"
            ),
        },
    ),
    retrieve=extend_schema(
        tags=["Vehicle Logs"],
        summary="Retrieve vehicle log",
        description="Retrieve the full representation of a log entry, including all attached media.",
        parameters=[_VEHICLE_PK_PARAMETER],
        responses={
            200: VehicleLogDetailSerializer,
            404: OpenApiResponse(
                response=ProblemDetailsSerializer,
                description="Vehicle or log not found",
            ),
        },
    ),
    create=extend_schema(
        tags=["Vehicle Logs"],
        summary="Create vehicle log",
        description=(
            "Create a new log entry for a vehicle. "
            "Optionally include a list of media files (photos or videos) "
            "to attach in the same atomic operation."
        ),
        parameters=[_VEHICLE_PK_PARAMETER],
        request=VehicleLogWriteSerializer,
        responses={
            201: VehicleLogDetailSerializer,
            400: OpenApiResponse(
                response=ProblemDetailsSerializer, description="Validation error"
            ),
            404: OpenApiResponse(
                response=ProblemDetailsSerializer, description="Vehicle not found"
            ),
        },
    ),
    partial_update=extend_schema(
        tags=["Vehicle Logs"],
        summary="Partially update vehicle log",
        description="Update the title or detail of a log entry. At least one field is required.",
        parameters=[_VEHICLE_PK_PARAMETER],
        request=VehicleLogUpdateSerializer,
        responses={
            200: VehicleLogDetailSerializer,
            400: OpenApiResponse(
                response=ProblemDetailsSerializer, description="Validation error"
            ),
            404: OpenApiResponse(
                response=ProblemDetailsSerializer,
                description="Vehicle or log not found",
            ),
        },
    ),
    destroy=extend_schema(
        tags=["Vehicle Logs"],
        summary="Delete vehicle log",
        description="Permanently delete a log entry and all its associated media files.",
        parameters=[_VEHICLE_PK_PARAMETER],
        responses={
            204: OpenApiResponse(description="Log deleted successfully"),
            404: OpenApiResponse(description="Vehicle or log not found"),
        },
    ),
)
class VehicleLogViewSet(
    GenericViewSet,
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    DestroyModelMixin,
):
    """
    Manages log entries (incidents, observations, cleanings, maintenance)
    nested under a parent vehicle.

    All actions are scoped to a single vehicle via the `vehicle_pk` URL
    kwarg: the queryset is always filtered by it, and object lookups are
    delegated to VehicleLogService so that a log belonging to a different
    vehicle cannot be retrieved, updated, or deleted through this endpoint.
    Status transitions are handled separately via the `update_status`
    action rather than through `partial_update`, since `VehicleLogUpdateSerializer`
    only allows editing `title`/`detail`.
    """

    serializer_class = VehicleLogListSerializer
    permission_classes = [VehicleLogPermissions]
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    ordering = ["created_by"]

    serializer_class_by_action = {
        "create": VehicleLogWriteSerializer,
        "partial_update": VehicleLogUpdateSerializer,
        "list": VehicleLogListSerializer,
        "retrieve": VehicleLogDetailSerializer,
        "update_status": VehicleLogStatusSerializer,
    }

    def get_vehicle_pk(self) -> int:
        """Extract and cast the parent vehicle's ID from the URL kwargs."""
        return int(self.kwargs["vehicle_pk"])

    def get_queryset(self):  # type: ignore
        """Scope the queryset to logs belonging to the parent vehicle only."""
        return VehicleLog.objects.filter(vehicle_id=self.get_vehicle_pk())

    def get_object(self):  # type: ignore
        """Delegate object lookup to VehicleLogService, scoped to the parent vehicle."""
        return VehicleLogService.get_by_id(self.get_vehicle_pk(), self.kwargs["pk"])

    def get_serializer_class(self):
        """Return the serializer registered for the current action, falling back to the list serializer."""
        return self.serializer_class_by_action.get(self.action, self.serializer_class)

    def create(self, request, *args, **kwargs):
        """
        Validate the incoming payload, create the log entry (and any
        attached media) via the service layer, and return the full detail
        representation rather than the write serializer's own (write-only)
        representation.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        read_serializer = VehicleLogDetailSerializer(
            instance, context=self.get_serializer_context()
        )
        return Response(
            read_serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def perform_create(self, serializer):  # type: ignore
        """Delegate log creation to VehicleLogService, attributing it to the requesting user."""
        return VehicleLogService.create(
            self.get_vehicle_pk(),
            created_by=self.request.user,  # type: ignore
            **serializer.validated_data,
        )

    def partial_update(self, request, *args, **kwargs):
        """
        Validate the incoming partial payload, update the log entry via
        the service layer, and return the full detail representation
        rather than the update serializer's own (write-only) representation.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = self.perform_update(serializer)

        read_serializer = VehicleLogDetailSerializer(
            instance, context=self.get_serializer_context()
        )
        return Response(read_serializer.data, status=status.HTTP_200_OK)

    def perform_update(self, serializer):  # type: ignore
        """Delegate log update to VehicleLogService, scoped to the parent vehicle."""
        return VehicleLogService.update(
            self.get_vehicle_pk(),
            self.kwargs["pk"],
            **serializer.validated_data,
        )

    def perform_destroy(self, instance):
        """Delegate log deletion (cascading to its media files) to VehicleLogService."""
        VehicleLogService.delete(self.get_vehicle_pk(), instance.pk)

    @extend_schema(
        tags=["Vehicle Logs"],
        summary="Update vehicle log status",
        description="Update the status of a log entry.",
        parameters=[_VEHICLE_PK_PARAMETER],
        request=VehicleLogStatusSerializer,
        responses={
            200: VehicleLogDetailSerializer,
            400: OpenApiResponse(
                response=ProblemDetailsSerializer, description="Validation error"
            ),
            404: OpenApiResponse(
                response=ProblemDetailsSerializer,
                description="Vehicle or log not found",
            ),
        },
    )
    @action(detail=True, methods=["patch"], url_path="status")
    def update_status(self, request, *args, **kwargs):
        """
        Validate the new status, apply the transition via the service
        layer, and return the full detail representation. Kept separate
        from `partial_update` so that status changes can carry their own
        transition rules independent of title/detail edits.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = VehicleLogService.update_status(
            self.get_vehicle_pk(),
            self.kwargs["pk"],
            **serializer.validated_data,
        )
        read_serializer = VehicleLogDetailSerializer(
            instance, context=self.get_serializer_context()
        )
        return Response(read_serializer.data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# MediaViewSet
# ---------------------------------------------------------------------------


_VEHICLE_LOG_PATH_PARAMETERS = [
    OpenApiParameter(
        name="vehicle_pk",
        type=OpenApiTypes.INT,
        location=OpenApiParameter.PATH,
        description="ID of the parent vehicle.",
    ),
    OpenApiParameter(
        name="log_pk",
        type=OpenApiTypes.INT,
        location=OpenApiParameter.PATH,
        description="ID of the parent vehicle log.",
    ),
]


@extend_schema_view(
    list=extend_schema(
        tags=["Media"],
        summary="List media files",
        description="Returns all media files attached to a specific vehicle log.",
        parameters=_VEHICLE_LOG_PATH_PARAMETERS,
        responses={
            200: MediaListSerializer(many=True),
            404: OpenApiResponse(
                response=ProblemDetailsSerializer,
                description="Vehicle or log not found",
            ),
        },
    ),
    retrieve=extend_schema(
        tags=["Media"],
        summary="Retrieve media file",
        description="Retrieve the full representation of a single media file.",
        parameters=_VEHICLE_LOG_PATH_PARAMETERS,
        responses={
            200: MediaDetailSerializer,
            404: OpenApiResponse(
                response=ProblemDetailsSerializer, description="Media file not found"
            ),
        },
    ),
    create=extend_schema(
        tags=["Media"],
        summary="Upload media file",
        description=(
            "Upload a single photo or video and attach it to a vehicle log.\n\n"
            "**Accepted formats**\n"
            "- Photos: `jpg`, `jpeg`, `png`, `webp`\n"
            "- Videos: `mp4`, `mov`, `avi`"
        ),
        parameters=_VEHICLE_LOG_PATH_PARAMETERS,
        request=MediaWriteSerializer,
        responses={
            201: MediaDetailSerializer,
            400: OpenApiResponse(
                response=ProblemDetailsSerializer,
                description="Validation error or missing file",
            ),
            404: OpenApiResponse(
                response=ProblemDetailsSerializer,
                description="Vehicle or log not found",
            ),
            422: OpenApiResponse(
                response=ProblemDetailsSerializer, description="Unsupported file type"
            ),
        },
    ),
    destroy=extend_schema(
        tags=["Media"],
        summary="Delete media file",
        description="Permanently delete a media file from storage and the database.",
        parameters=_VEHICLE_LOG_PATH_PARAMETERS,
        responses={
            204: OpenApiResponse(description="Media file deleted successfully"),
            404: OpenApiResponse(
                response=ProblemDetailsSerializer, description="Media file not found"
            ),
        },
    ),
)
class MediaViewSet(
    GenericViewSet,
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    DestroyModelMixin,
):
    """
    Manages media files (photos and videos) attached to a vehicle log.

    Nested under both `vehicle_pk` and `log_pk`, but note that `get_object`
    only scopes by the media file's own `pk` (via MediaService.get_by_id),
    not by the parent vehicle/log — the path parameters are used for
    listing and creation, but a retrieve/destroy by `pk` is not currently
    validated against the parent log it claims to belong to. Update is not
    supported: media files are immutable once uploaded and must be deleted
    and re-uploaded instead.
    """

    serializer_class = MediaListSerializer
    permission_classes = [MediaPermissions]

    serializer_class_by_action = {
        "create": MediaWriteSerializer,
        "list": MediaListSerializer,
        "retrieve": MediaDetailSerializer,
    }

    def get_vehicle_pk(self) -> int:
        """Extract and cast the parent vehicle's ID from the URL kwargs."""
        return int(self.kwargs["vehicle_pk"])

    def get_log_pk(self) -> int:
        """Extract and cast the parent log's ID from the URL kwargs."""
        return int(self.kwargs["log_pk"])

    # REVISAR LOGICA DE get_object y get_queryset
    def get_queryset(self):  # type: ignore
        """Scope the queryset to media files belonging to the parent vehicle log only."""
        return MediaService.list_by_log(self.get_vehicle_pk(), self.get_log_pk())

    def get_object(self):  # type: ignore
        """Delegate object lookup to MediaService, scoped only by the media file's own ID."""
        return MediaService.get_by_id(self.kwargs["pk"])

    def get_serializer_class(self):
        """Return the serializer registered for the current action, falling back to the list serializer."""
        return self.serializer_class_by_action.get(self.action, self.serializer_class)

    def create(self, request, *args, **kwargs):
        """
        Validate the incoming file, create the media record via the
        service layer, and return the full detail representation rather
        than the write serializer's own (write-only) representation.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        read_serializer = MediaDetailSerializer(
            instance, context=self.get_serializer_context()
        )
        return Response(
            read_serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def perform_create(self, serializer):  # type: ignore
        """
        Confirm the parent log exists and belongs to the parent vehicle
        before attaching the uploaded file to it via MediaService.
        """
        log = VehicleLogService.get_by_id(self.get_vehicle_pk(), self.get_log_pk())
        return MediaService.create(log.pk, file=serializer.validated_data["file"])

    def perform_destroy(self, instance):
        """Delegate media file deletion (storage and database) to MediaService."""
        MediaService.delete(instance.pk)


@extend_schema(
    tags=["Dashboard"],
    summary="Get dashboard data",
    description=(
        "Returns aggregated statistics for the admin dashboard: summary KPIs, "
        "log distribution by status/type, top vehicles and users by log count, "
        "recent activity and media stats. "
        "`date_from`/`date_to` are optional and filter logs by creation date; "
        "`summary.total_vehicles` and the live counters "
        "(`logs_today`, `logs_this_week`, `logs_this_month`) are never affected "
        "by these filters."
    ),
    parameters=[_DATE_FROM_PARAM, _DATE_TO_PARAM],
    responses={
        200: DashboardSerializer,
        400: OpenApiResponse(
            response=ProblemDetailsSerializer, description="Invalid query parameters"
        ),
    },
)
class DashboardView(APIView):
    """
    Returns aggregated statistics for the admin dashboard.

    Restricted to authenticated admin users only. Unlike the other
    viewsets in this project, this is a plain APIView rather than a
    GenericViewSet, since it exposes a single read-only aggregation
    endpoint with no model-backed CRUD operations.
    """

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, *args, **kwargs):
        """
        Validate the optional date-range filters, delegate the
        aggregation to DashboardService, and serialize the result.
        """
        query = DashboardQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        data = DashboardService.get_dashboard_data(
            date_from=query.validated_data.get("date_from"),
            date_to=query.validated_data.get("date_to"),
        )

        serializer = DashboardSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)
