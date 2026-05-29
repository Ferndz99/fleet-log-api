import django_filters

from apps.memberships.membership.domain.models import Membership


class MembershipFilter(django_filters.FilterSet):
    invited = django_filters.BooleanFilter(method="filter_invited")

    joined_after = django_filters.DateTimeFilter(
        field_name="joined_at", lookup_expr="gte"
    )

    joined_before = django_filters.DateTimeFilter(
        field_name="joined_at", lookup_expr="lte"
    )

    class Meta:
        model = Membership
        fields = ["is_active"]

    def filter_invited(self, queryset, name, value):
        if value:
            return queryset.filter(joined_at__isnull=True)
        return queryset.filter(joined_at__isnull=False)
