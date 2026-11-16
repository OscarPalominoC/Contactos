"""Filtros de llamadas.

`pendiente=true` devuelve solo lo que hay que llamar: no realizadas, con fecha válida y cuyo
contacto (o titular de la moto) está habilitado y autoriza ese canal. `consentimiento` filtra por esa autorización
sin ocultar el historial.
"""

from typing import Any

import django_filters
from django.db.models import Case, IntegerField, Q, Value, When

from apps.comun.fechas_util import ANO_MAXIMO, ANO_MINIMO
from apps.llamadas.models import ESTADOS_LLAMADA, LlamadaCumpleanos, LlamadaRtm, LlamadaSoat


def _ordenar_pendientes(queryset: Any, *desempate: str) -> Any:
    return (
        queryset.exclude(estado="realizada")
        .annotate(
            _orden_pendiente=Case(
                When(estado="sin_estado", then=Value(0)),
                When(num_llamadas=0, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        )
        .order_by("_orden_pendiente", *desempate)
    )


class FiltroLlamadasCumpleanos(django_filters.FilterSet):  # type: ignore[misc]
    fecha = django_filters.DateFilter(field_name="fecha", lookup_expr="date")
    desde = django_filters.DateFilter(field_name="fecha", lookup_expr="date__gte")
    hasta = django_filters.DateFilter(field_name="fecha", lookup_expr="date__lte")
    estado = django_filters.ChoiceFilter(choices=ESTADOS_LLAMADA)
    nip = django_filters.CharFilter(field_name="contacto_id")
    pendiente = django_filters.BooleanFilter(method="filtrar_pendiente")
    consentimiento = django_filters.BooleanFilter(
        field_name="contacto__contactar_cumpleanos", help_text="El contacto autoriza llamadas de cumpleaños."
    )

    class Meta:
        model = LlamadaCumpleanos
        fields = ["fecha", "desde", "hasta", "estado", "nip", "pendiente", "consentimiento"]

    def filtrar_pendiente(self, queryset: Any, name: str, value: bool) -> Any:
        if value:
            validas = queryset.filter(contacto__contactar_cumpleanos=True, contacto__estado="habilitado")
            return _ordenar_pendientes(validas, "-fecha", "-id")
        return queryset


class _FiltroLlamadasPlaca(django_filters.FilterSet):  # type: ignore[misc]
    campo_consentimiento = ""

    fecha = django_filters.DateFilter(field_name="fecha")
    desde = django_filters.DateFilter(field_name="fecha", lookup_expr="gte")
    hasta = django_filters.DateFilter(field_name="fecha", lookup_expr="lte")
    estado = django_filters.ChoiceFilter(choices=ESTADOS_LLAMADA)
    placa = django_filters.CharFilter(field_name="moto_id")
    pendiente = django_filters.BooleanFilter(method="filtrar_pendiente")
    consentimiento = django_filters.BooleanFilter(
        method="filtrar_consentimiento", help_text="El titular de la moto autoriza este canal."
    )

    def filtrar_consentimiento(self, queryset: Any, name: str, value: bool) -> Any:
        return queryset.filter(**{f"moto__contacto__{self.campo_consentimiento}": value})

    def filtrar_pendiente(self, queryset: Any, name: str, value: bool) -> Any:
        if value:
            validas = queryset.filter(
                Q(fecha__year__gte=ANO_MINIMO, fecha__year__lte=ANO_MAXIMO),
                moto__contacto__estado="habilitado",
                **{f"moto__contacto__{self.campo_consentimiento}": True},
            )
            return _ordenar_pendientes(validas, "-fecha", "id")
        return queryset


class FiltroLlamadasRtm(_FiltroLlamadasPlaca):
    campo_consentimiento = "contactar_rtm"

    class Meta:
        model = LlamadaRtm
        fields = ["fecha", "desde", "hasta", "estado", "placa", "pendiente", "consentimiento"]


class FiltroLlamadasSoat(_FiltroLlamadasPlaca):
    campo_consentimiento = "contactar_soat"

    class Meta:
        model = LlamadaSoat
        fields = ["fecha", "desde", "hasta", "estado", "placa", "pendiente", "consentimiento"]
