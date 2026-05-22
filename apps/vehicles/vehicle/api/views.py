from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
)
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from drf_spectacular.types import OpenApiTypes

from apps.vehicles.vehicle.api.serializers import (
    MediaDetailSerializer,
    MediaListSerializer,
    MediaWriteSerializer,
    VehicleDetailSerializer,
    VehicleListSerializer,
    VehicleLogDetailSerializer,
    VehicleLogListSerializer,
    VehicleLogUpdateSerializer,
    VehicleLogWriteSerializer,
    VehicleUpdateSerializer,
    VehicleWriteSerializer,
)
from apps.vehicles.vehicle.domain.services import MediaService, VehicleLogService, VehicleService


# ---------------------------------------------------------------------------
# VehicleViewSet
# ---------------------------------------------------------------------------


@extend_schema_view(
    list=extend_schema(
        tags=["Vehicles"],
        summary="List vehicles",
        description="Returns a compact list of all registered vehicles including their log count.",
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
)
class VehicleViewSet(
    GenericViewSet,
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    DestroyModelMixin,
):
    serializer_class = VehicleListSerializer
    permission_classes = [IsAuthenticated]

    serializer_class_by_action = {
        "create": VehicleWriteSerializer,
        "partial_update": VehicleUpdateSerializer,
        "list": VehicleListSerializer,
        "retrieve": VehicleDetailSerializer,
    }

    permission_classes_by_action = {
        "create": [IsAuthenticated, IsAdminUser],
        "list": [IsAuthenticated],
        "retrieve": [IsAuthenticated],
        "partial_update": [IsAuthenticated, IsAdminUser],
        "destroy": [IsAuthenticated, IsAdminUser],
    }

    def get_queryset(self):  # type: ignore
        return VehicleService.list_all()

    def get_object(self):  # type: ignore
        return VehicleService.get_by_id(self.kwargs["pk"])

    def get_serializer_class(self):
        return self.serializer_class_by_action.get(self.action, self.serializer_class)

    def get_permissions(self):
        permission_classes = self.permission_classes_by_action.get(
            self.action, self.permission_classes
        )
        return [permission() for permission in permission_classes]

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
    permission_classes = [IsAuthenticated]

    serializer_class_by_action = {
        "create": VehicleLogWriteSerializer,
        "partial_update": VehicleLogUpdateSerializer,
        "list": VehicleLogListSerializer,
        "retrieve": VehicleLogDetailSerializer,
    }

    permission_classes_by_action = {
        "create": [IsAuthenticated],
        "list": [IsAuthenticated],
        "retrieve": [IsAuthenticated],
        "partial_update": [IsAuthenticated],
        "destroy": [IsAuthenticated, IsAdminUser],
    }

    def get_vehicle_pk(self) -> int:
        return int(self.kwargs["vehicle_pk"])

    def get_queryset(self):  # type: ignore
        return VehicleLogService.list_by_vehicle(self.get_vehicle_pk())

    def get_object(self):  # type: ignore
        return VehicleLogService.get_by_id(self.get_vehicle_pk(), self.kwargs["pk"])

    def get_serializer_class(self):
        return self.serializer_class_by_action.get(self.action, self.serializer_class)

    def get_permissions(self):
        permission_classes = self.permission_classes_by_action.get(
            self.action, self.permission_classes
        )
        return [permission() for permission in permission_classes]

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
            created_by=self.request.user, # type: ignore
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
    permission_classes = [IsAuthenticated]

    serializer_class_by_action = {
        "create": MediaWriteSerializer,
        "list": MediaListSerializer,
        "retrieve": MediaDetailSerializer,
    }

    permission_classes_by_action = {
        "create": [IsAuthenticated],
        "list": [IsAuthenticated],
        "retrieve": [IsAuthenticated],
        "destroy": [IsAuthenticated, IsAdminUser],
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

    def get_permissions(self):
        permission_classes = self.permission_classes_by_action.get(
            self.action, self.permission_classes
        )
        return [permission() for permission in permission_classes]

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
