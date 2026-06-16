import django_filters


from apps.vehicles.vehicle.domain.models import Vehicle


# ─── Filter class ────────────────────────────────────────────────────────────


class VehicleFilter(django_filters.FilterSet):
    """
    Filtros disponibles para el endpoint de listado de vehículos.
    """

    # Rango de año de fabricación
    year_min = django_filters.NumberFilter(field_name="year", lookup_expr="gte")
    year_max = django_filters.NumberFilter(field_name="year", lookup_expr="lte")

    # Filtros exactos
    brand = django_filters.CharFilter(field_name="brand", lookup_expr="iexact")
    model = django_filters.CharFilter(field_name="model", lookup_expr="iexact")
    # is_active = django_filters.BooleanFilter(field_name="is_active")

    # Rango de logs
    min_logs = django_filters.NumberFilter(field_name="log_count", lookup_expr="gte")
    max_logs = django_filters.NumberFilter(field_name="log_count", lookup_expr="lte")

    class Meta:
        model = Vehicle
        fields = [
            "brand",
            "model",
            # "is_active",
            "year_min",
            "year_max",
            "min_logs",
            "max_logs",
        ]
