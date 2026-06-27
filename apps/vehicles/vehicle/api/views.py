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
# ---------------------------------------------------------------------------
# VehicleViewSet
# ---------------------------------------------------------------------------


_SEARCH_PARAM = OpenApiParameter(
    name="search",
    type=str,
    location=OpenApiParameter.QUERY,
    description=(
        "Búsqueda de texto libre. Aplica sobre **patent**, **brand** y **model**. "
        "Ejemplo: `search=Toyota`"
    ),
)

_ORDERING_PARAM = OpenApiParameter(
    name="ordering",
    type=str,
    location=OpenApiParameter.QUERY,
    description=(
        "Campo por el que ordenar los resultados. "
        "Prefija con `-` para orden descendente. "
        "Valores permitidos: `patent`, `brand`, `model`, `year`, `log_count`, `created_at`. "
        "Ejemplo: `ordering=-year`"
    ),
)

_FILTER_PARAMS = [
    OpenApiParameter(
        "brand",
        str,
        OpenApiParameter.QUERY,
        description="Filtrar por marca (insensible a mayúsculas). Ej: `brand=Ford`",
    ),
    OpenApiParameter(
        "model",
        str,
        OpenApiParameter.QUERY,
        description="Filtrar por modelo (insensible a mayúsculas). Ej: `model=Ranger`",
    ),
    OpenApiParameter(
        "is_active",
        bool,
        OpenApiParameter.QUERY,
        description="Estado del vehículo. `true` = activos, `false` = inactivos.",
    ),
    OpenApiParameter(
        "year_min",
        int,
        OpenApiParameter.QUERY,
        description="Año de fabricación mínimo (inclusivo). Ej: `year_min=2018`",
    ),
    OpenApiParameter(
        "year_max",
        int,
        OpenApiParameter.QUERY,
        description="Año de fabricación máximo (inclusivo). Ej: `year_max=2023`",
    ),
    OpenApiParameter(
        "min_logs",
        int,
        OpenApiParameter.QUERY,
        description="Cantidad mínima de logs asociados.",
    ),
    OpenApiParameter(
        "max_logs",
        int,
        OpenApiParameter.QUERY,
        description="Cantidad máxima de logs asociados.",
    ),
]


# Agregar este parámetro junto a los otros _PARAMS al inicio del archivo
_PATENT_PARAM = OpenApiParameter(
    name="patent",
    location=OpenApiParameter.QUERY,
    description="Vehicle patent plate to search for (exact match).",
    required=True,
    type=str,
)


_DATE_FROM_PARAM = OpenApiParameter(
    name="date_from",
    type=str,
    location=OpenApiParameter.QUERY,
    required=False,
    description="Fecha de inicio (inclusive) para filtrar el dashboard. Formato ISO 8601. Ej: `2026-06-01`",
)

_DATE_TO_PARAM = OpenApiParameter(
    name="date_to",
    type=str,
    location=OpenApiParameter.QUERY,
    required=False,
    description="Fecha de término (inclusive) para filtrar el dashboard. Formato ISO 8601. Ej: `2026-06-22`",
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
        responses=VehicleListSerializer(many=True),
    ),
    retrieve=extend_schema(
        tags=["Vehicles"],
        summary="Retrieve vehicle",
        description="Retrieve the full representation of a vehicle including its log list.",
        responses=VehicleDetailSerializer,
    ),
    create=extend_schema(
        tags=["Vehicles"],
        summary="Create vehicle",
        description="Register a new vehicle in the system.",
        request=VehicleWriteSerializer,
        responses={
            201: VehicleDetailSerializer,
            400: OpenApiResponse(description="Validation error"),
            409: OpenApiResponse(
                description="A vehicle with this patent already exists"
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
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="Vehicle not found"),
            409: OpenApiResponse(
                description="Patent already in use by another vehicle"
            ),
        },
    ),
    destroy=extend_schema(
        tags=["Vehicles"],
        summary="Delete vehicle",
        description="Permanently delete a vehicle along with all its logs and media files.",
        responses={
            204: OpenApiResponse(description="Vehicle deleted successfully"),
            404: OpenApiResponse(description="Vehicle not found"),
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
                description="Missing required 'patent' query parameter"
            ),
            404: OpenApiResponse(description="Vehicle not found"),
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

    # permission_classes_by_action = {
    #     "create": [IsAuthenticated, IsAdminUser],
    #     "list": [AllowAny],
    #     "retrieve": [AllowAny],
    #     "partial_update": [IsAuthenticated, IsAdminUser],
    #     "destroy": [IsAuthenticated, IsAdminUser],
    #     "by_patent": [AllowAny],
    # }

    def get_queryset(self):  # type: ignore
        return Vehicle.objects.annotate(log_count=Count("logs")).all()

    def get_object(self):  # type: ignore
        return VehicleService.get_by_id(self.kwargs["pk"])

    def get_serializer_class(self):
        return self.serializer_class_by_action.get(self.action, self.serializer_class)

    # def get_permissions(self):
    #     permission_classes = self.permission_classes_by_action.get(
    #         self.action, self.permission_classes
    #     )
    #     return [permission() for permission in permission_classes]

    def create(self, request, *args, **kwargs):
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
        return VehicleService.create(**serializer.validated_data)

    def partial_update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = self.perform_update(serializer)

        read_serializer = VehicleDetailSerializer(
            instance, context=self.get_serializer_context()
        )
        return Response(read_serializer.data, status=status.HTTP_200_OK)

    def perform_update(self, serializer):  # type: ignore
        return VehicleService.update(self.kwargs["pk"], **serializer.validated_data)

    def perform_destroy(self, instance):
        VehicleService.delete(instance.pk)

    @action(detail=False, methods=["get"], url_path="by-patent")
    def by_patent(self, request, *args, **kwargs):
        patent = request.query_params.get("patent", "").strip()

        if not patent:
            return Response(
                {"detail": "The 'patent' query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
        responses=VehicleLogListSerializer(many=True),
    ),
    retrieve=extend_schema(
        tags=["Vehicle Logs"],
        summary="Retrieve vehicle log",
        description="Retrieve the full representation of a log entry, including all attached media.",
        parameters=[_VEHICLE_PK_PARAMETER],
        responses=VehicleLogDetailSerializer,
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
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="Vehicle not found"),
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
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="Vehicle or log not found"),
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
        return int(self.kwargs["vehicle_pk"])

    def get_queryset(self):  # type: ignore
        return VehicleLog.objects.filter(vehicle_id=self.get_vehicle_pk())

    def get_object(self):  # type: ignore
        return VehicleLogService.get_by_id(self.get_vehicle_pk(), self.kwargs["pk"])

    def get_serializer_class(self):
        return self.serializer_class_by_action.get(self.action, self.serializer_class)

    def create(self, request, *args, **kwargs):
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
        return VehicleLogService.create(
            self.get_vehicle_pk(),
            created_by=self.request.user,  # type: ignore
            **serializer.validated_data,
        )

    def partial_update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = self.perform_update(serializer)

        read_serializer = VehicleLogDetailSerializer(
            instance, context=self.get_serializer_context()
        )
        return Response(read_serializer.data, status=status.HTTP_200_OK)

    def perform_update(self, serializer):  # type: ignore
        return VehicleLogService.update(
            self.get_vehicle_pk(),
            self.kwargs["pk"],
            **serializer.validated_data,
        )

    def perform_destroy(self, instance):
        VehicleLogService.delete(self.get_vehicle_pk(), instance.pk)

    @extend_schema(
        tags=["Vehicle Logs"],
        summary="Update vehicle log status",
        description="Update the status of a log entry.",
        parameters=[_VEHICLE_PK_PARAMETER],
        request=VehicleLogStatusSerializer,
        responses={
            200: VehicleLogDetailSerializer,
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="Vehicle or log not found"),
        },
    )
    @action(detail=True, methods=["patch"], url_path="status")
    def update_status(self, request, *args, **kwargs):
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
        responses=MediaListSerializer(many=True),
    ),
    retrieve=extend_schema(
        tags=["Media"],
        summary="Retrieve media file",
        description="Retrieve the full representation of a single media file.",
        parameters=_VEHICLE_LOG_PATH_PARAMETERS,
        responses=MediaDetailSerializer,
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
            400: OpenApiResponse(description="Validation error or missing file"),
            404: OpenApiResponse(description="Vehicle or log not found"),
            422: OpenApiResponse(description="Unsupported file type"),
        },
    ),
    destroy=extend_schema(
        tags=["Media"],
        summary="Delete media file",
        description="Permanently delete a media file from storage and the database.",
        parameters=_VEHICLE_LOG_PATH_PARAMETERS,
        responses={
            204: OpenApiResponse(description="Media file deleted successfully"),
            404: OpenApiResponse(description="Media file not found"),
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
    serializer_class = MediaListSerializer
    permission_classes = [MediaPermissions]

    serializer_class_by_action = {
        "create": MediaWriteSerializer,
        "list": MediaListSerializer,
        "retrieve": MediaDetailSerializer,
    }

    def get_vehicle_pk(self) -> int:
        return int(self.kwargs["vehicle_pk"])

    def get_log_pk(self) -> int:
        return int(self.kwargs["log_pk"])

    def get_queryset(self):  # type: ignore
        return MediaService.list_by_log(self.get_vehicle_pk(), self.get_log_pk())

    def get_object(self):  # type: ignore
        return MediaService.get_by_id(self.kwargs["pk"])

    def get_serializer_class(self):
        return self.serializer_class_by_action.get(self.action, self.serializer_class)

    def create(self, request, *args, **kwargs):
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
        log = VehicleLogService.get_by_id(self.get_vehicle_pk(), self.get_log_pk())
        return MediaService.create(log.pk, file=serializer.validated_data["file"])

    def perform_destroy(self, instance):
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
        400: OpenApiResponse(description="Invalid query parameters"),
    },
)
class DashboardView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, *args, **kwargs):
        query = DashboardQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        data = DashboardService.get_dashboard_data(
            date_from=query.validated_data.get("date_from"),
            date_to=query.validated_data.get("date_to"),
        )

        serializer = DashboardSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)
