from rest_framework.permissions import BasePermission


class VehiclePermission(BasePermission):
    """
    Permission class centralizada para VehicleViewSet
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        perms_map = {
            "list": "vehicles.view_vehicle",
            "retrieve": "vehicles.view_vehicle",
            "create": "vehicles.add_vehicle",
            "partial_update": "vehicles.change_vehicle",
            "destroy": "vehicles.delete_vehicle",
            # 🔥 acción custom
            "by_patent": "vehicles.search_vehicle_by_patent",
        }

        required_perm = perms_map.get(view.action)

        # si no está definido, bloquea por seguridad
        if not required_perm:
            return False

        return request.user.has_perm(required_perm)


class VehicleLogPermissions(BasePermission):
    """
    Permission class centralizada para VehicleLogViewSet
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        perms_map = {
            "list": "vehicles.view_vehiclelog",
            "retrieve": "vehicles.view_vehiclelog",
            "create": "vehicles.add_vehiclelog",
            "partial_update": "vehicles.change_vehiclelog",
            "destroy": "vehicles.delete_vehiclelog",
            # 🔥 acción custom
            "update_status": "vehicles.update_vehiclelog_status",
        }

        required_perm = perms_map.get(view.action)

        if not required_perm:
            return False

        return request.user.has_perm(required_perm)


class MediaPermissions(BasePermission):
    """
    Permission class centralizada para VehicleLogViewSet
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        perms_map = {
            "list": "vehicles.view_media",
            "retrieve": "vehicles.view_media",
            "create": "vehicles.add_media",
            "partial_update": "vehicles.change_media",
            "destroy": "vehicles.delete_media",
        }

        required_perm = perms_map.get(view.action)

        if not required_perm:
            return False

        return request.user.has_perm(required_perm)
