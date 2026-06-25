from rest_framework_nested import routers
from django.urls import path

from apps.vehicles.vehicle.api.views import (
    DashboardView,
    MediaViewSet,
    VehicleLogViewSet,
    VehicleViewSet,
)

# /vehicles/
router = routers.SimpleRouter()
router.register(r"vehicles", VehicleViewSet, basename="vehicle")

# /vehicles/{vehicle_pk}/logs/
logs_router = routers.NestedDefaultRouter(router, r"vehicles", lookup="vehicle")
logs_router.register(r"logs", VehicleLogViewSet, basename="vehicle-log")

# /vehicles/{vehicle_pk}/logs/{log_pk}/media/
media_router = routers.NestedDefaultRouter(logs_router, r"logs", lookup="log")
media_router.register(r"media", MediaViewSet, basename="vehicle-log-media")

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
] + router.urls + logs_router.urls + media_router.urls

# urlpatterns = router.urls + logs_router.urls + media_router.urls
