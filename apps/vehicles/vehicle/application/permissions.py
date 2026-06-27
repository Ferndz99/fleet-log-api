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
