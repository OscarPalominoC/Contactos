"""Filtros de usuarios."""

import django_filters

from apps.cuentas.models import ROLES, Usuario


class FiltroUsuarios(django_filters.FilterSet):  # type: ignore[misc]
    rol = django_filters.ChoiceFilter(choices=ROLES)
    activo = django_filters.BooleanFilter(field_name="is_active")
    q = django_filters.CharFilter(method="buscar")

    class Meta:
        model = Usuario
        fields = ["rol", "activo", "q"]

    def buscar(self, queryset, nombre, valor):  # type: ignore[no-untyped-def]
        from django.db.models import Q

        return queryset.filter(Q(nip__icontains=valor) | Q(nombre__icontains=valor))
