"""Filtros de revisiones y SOAT."""

import django_filters
from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.revisiones.models import ESTADOS_DOCUMENTO, Revision, Soat


class _FiltroVigencia(django_filters.FilterSet):  # type: ignore[misc]
    campo_vencimiento = "fecha_venc_certificado"
    campo_numero = "certificado"

    def filtrar_estado_actual(self, queryset: QuerySet, nombre: str, valor: str) -> QuerySet:  # type: ignore[type-arg]
        """VIGENTE/VENCIDO se calculan con la fecha; los demás estados son los guardados."""
        hoy = timezone.localdate()
        campo = self.campo_vencimiento
        manuales = ["DUPLICADO", "ANULADO", "NO"]
        if valor == "VIGENTE":
            return queryset.exclude(estado__in=manuales).filter(**{f"{campo}__gte": hoy})
        if valor == "VENCIDO":
            return queryset.exclude(estado__in=manuales).filter(**{f"{campo}__lt": hoy})
        return queryset.filter(estado=valor)

    def buscar(self, queryset: QuerySet, nombre: str, valor: str) -> QuerySet:  # type: ignore[type-arg]
        """Placa (prefijo, sin espacios ni guiones) o número del documento (prefijo, sin importar mayúsculas)."""
        limpio = valor.strip()
        if not limpio:
            return queryset
        placa = limpio.replace(" ", "").replace("-", "").upper()
        return queryset.filter(Q(moto__placa__startswith=placa) | Q(**{f"{self.campo_numero}__istartswith": limpio}))


class FiltroRevisiones(_FiltroVigencia):
    campo_vencimiento = "fecha_venc_certificado"
    campo_numero = "certificado"

    estado = django_filters.ChoiceFilter(choices=ESTADOS_DOCUMENTO, method="filtrar_estado_actual")
    placa = django_filters.CharFilter(field_name="moto_id")
    q = django_filters.CharFilter(method="buscar", help_text="Busca por placa o por número de certificado.")
    vence_desde = django_filters.DateFilter(field_name="fecha_venc_certificado", lookup_expr="gte")
    vence_hasta = django_filters.DateFilter(field_name="fecha_venc_certificado", lookup_expr="lte")

    class Meta:
        model = Revision
        fields = ["estado", "placa", "q", "vence_desde", "vence_hasta"]


class FiltroSoats(_FiltroVigencia):
    campo_vencimiento = "fecha_venc_soat"
    campo_numero = "soat"

    estado = django_filters.ChoiceFilter(choices=ESTADOS_DOCUMENTO, method="filtrar_estado_actual")
    placa = django_filters.CharFilter(field_name="moto_id")
    q = django_filters.CharFilter(method="buscar", help_text="Busca por placa o por número de póliza.")
    vence_desde = django_filters.DateFilter(field_name="fecha_venc_soat", lookup_expr="gte")
    vence_hasta = django_filters.DateFilter(field_name="fecha_venc_soat", lookup_expr="lte")

    class Meta:
        model = Soat
        fields = ["estado", "placa", "q", "vence_desde", "vence_hasta"]
