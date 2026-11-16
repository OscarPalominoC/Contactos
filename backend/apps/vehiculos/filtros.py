"""Filtros de vehículos."""

import django_filters
from django.db.models import QuerySet

from apps.vehiculos.models import Linea, Marca, Moto


class FiltroMotos(django_filters.FilterSet):  # type: ignore[misc]
    nip_contacto = django_filters.CharFilter(field_name="contacto_id")
    marca = django_filters.CharFilter(field_name="marca", lookup_expr="iexact")
    q = django_filters.CharFilter(method="buscar", help_text="Busca por placa.")

    class Meta:
        model = Moto
        fields = ["nip_contacto", "marca", "q"]

    def buscar(self, queryset: QuerySet[Moto], nombre: str, valor: str) -> QuerySet[Moto]:
        valor = valor.replace(" ", "").upper()
        return queryset.filter(placa__startswith=valor) if valor else queryset


class FiltroMarcas(django_filters.FilterSet):  # type: ignore[misc]
    q = django_filters.CharFilter(field_name="nombre", lookup_expr="icontains")

    class Meta:
        model = Marca
        fields = ["q"]


class FiltroLineas(django_filters.FilterSet):  # type: ignore[misc]
    marca = django_filters.CharFilter(field_name="marca_id")
    q = django_filters.CharFilter(field_name="linea", lookup_expr="icontains")

    class Meta:
        model = Linea
        fields = ["marca", "q"]
