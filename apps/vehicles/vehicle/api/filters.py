import django_filters
from django.utils.translation import gettext_lazy as _

from apps.vehicles.vehicle.domain.models import Vehicle


# ─── Filter class ────────────────────────────────────────────────────────────


class VehicleFilter(django_filters.FilterSet):
    """
    Available filters for the vehicle list endpoint.

    `year_min`/`year_max` and `min_logs`/`max_logs` define inclusive
    ranges rather than exact matches, while `brand`/`model` are exact
    (case-insensitive) matches. `min_logs`/`max_logs` rely on the
    `log_count` annotation added in `VehicleViewSet.get_queryset`, so this
    filter only works against that annotated queryset, not a plain
    `Vehicle.objects.all()`. `is_active` is commented out pending the
    introduction of real permission classes and activation/deactivation
    logic.
    """

    # Rango de año de fabricación
    year_min = django_filters.NumberFilter(
        field_name="year",
        lookup_expr="gte",
        help_text=_("Minimum manufacturing year (inclusive)."),
    )
    year_max = django_filters.NumberFilter(
        field_name="year",
        lookup_expr="lte",
        help_text=_("Maximum manufacturing year (inclusive)."),
    )

    # Filtros exactos
    brand = django_filters.CharFilter(
        field_name="brand",
        lookup_expr="iexact",
        help_text=_("Filter by brand (case-insensitive, exact match)."),
    )
    model = django_filters.CharFilter(
        field_name="model",
        lookup_expr="iexact",
        help_text=_("Filter by model (case-insensitive, exact match)."),
    )
    # is_active = django_filters.BooleanFilter(field_name="is_active")

    # Rango de logs
    min_logs = django_filters.NumberFilter(
        field_name="log_count",
        lookup_expr="gte",
        help_text=_("Minimum number of associated logs (inclusive)."),
    )
    max_logs = django_filters.NumberFilter(
        field_name="log_count",
        lookup_expr="lte",
        help_text=_("Maximum number of associated logs (inclusive)."),
    )

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
