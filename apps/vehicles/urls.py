from rest_framework_nested import routers

from apps.vehicles.vehicle.api.views import MediaViewSet, VehicleLogViewSet, VehicleViewSet

# /vehicles/
router = routers.SimpleRouter()
router.register(r"vehicles", VehicleViewSet, basename="vehicle")

# /vehicles/{vehicle_pk}/logs/
logs_router = routers.NestedDefaultRouter(router, r"vehicles", lookup="vehicle")
logs_router.register(r"logs", VehicleLogViewSet, basename="vehicle-log")

# /vehicles/{vehicle_pk}/logs/{log_pk}/media/
media_router = routers.NestedDefaultRouter(logs_router, r"logs", lookup="log")
media_router.register(r"media", MediaViewSet, basename="vehicle-log-media")

urlpatterns = router.urls + logs_router.urls + media_router.urls
