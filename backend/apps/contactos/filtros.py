"""Filtros de contactos.

`cumple_desde`/`cumple_hasta` buscan cumpleaños (día y mes, sin año) dentro de un rango de fechas,
incluso si el rango cruza el fin de año. Un rango de 365 días o más trae a todos los que tienen fecha.
"""

from datetime import date
from typing import Any

import django_filters
from django.db.models import F, Q, QuerySet
from rest_framework.exceptions import ValidationError

from apps.contactos.models import ESTADOS_CONTACTO, MESES, Contacto


class FiltroContactos(django_filters.FilterSet):  # type: ignore[misc]
    estado = django_filters.ChoiceFilter(choices=ESTADOS_CONTACTO)
    mes_nac = django_filters.ChoiceFilter(choices=MESES)
    dia_nac = django_filters.NumberFilter()
    q = django_filters.CharFilter(method="buscar", help_text="Busca por documento o nombre.")
    contactar_cumpleanos = django_filters.BooleanFilter()
    contactar_soat = django_filters.BooleanFilter()
    contactar_rtm = django_filters.BooleanFilter()
    cumple_desde = django_filters.DateFilter(
        method="sin_filtrar", help_text="Cumpleaños desde esta fecha (AAAA-MM-DD)."
    )
    cumple_hasta = django_filters.DateFilter(
        method="sin_filtrar", help_text="Cumpleaños hasta esta fecha (AAAA-MM-DD)."
    )

    class Meta:
        model = Contacto
        fields = [
            "estado",
            "mes_nac",
            "dia_nac",
            "q",
            "contactar_cumpleanos",
            "contactar_soat",
            "contactar_rtm",
            "cumple_desde",
            "cumple_hasta",
        ]

    def sin_filtrar(self, queryset: QuerySet[Contacto], nombre: str, valor: Any) -> QuerySet[Contacto]:
        return queryset  # el rango se aplica completo en filter_queryset

    def filter_queryset(self, queryset: QuerySet[Contacto]) -> QuerySet[Contacto]:
        queryset = super().filter_queryset(queryset)
        desde: date | None = self.form.cleaned_data.get("cumple_desde")
        hasta: date | None = self.form.cleaned_data.get("cumple_hasta")
        if desde is None and hasta is None:
            return queryset
        inicio_rango: date = desde or hasta  # type: ignore[assignment]
        fin_rango: date = hasta or desde  # type: ignore[assignment]
        if inicio_rango > fin_rango:
            raise ValidationError({"cumple_desde": ["La fecha inicial no puede ser posterior a la final."]})
        con_fecha = queryset.filter(dia_nac__gte=1, mes_nac__gte=1)
        if (fin_rango - inicio_rango).days >= 365:
            return con_fecha
        # Clave MMDD: el 29 de febrero (229) cae entre el 28 (228) y el 1 de marzo (301) en años no bisiestos.
        clave = con_fecha.annotate(_mmdd=F("mes_nac") * 100 + F("dia_nac"))
        inicio = inicio_rango.month * 100 + inicio_rango.day
        fin = fin_rango.month * 100 + fin_rango.day
        if inicio <= fin:
            return clave.filter(_mmdd__gte=inicio, _mmdd__lte=fin)
        return clave.filter(Q(_mmdd__gte=inicio) | Q(_mmdd__lte=fin))

    def buscar(self, queryset: QuerySet[Contacto], nombre: str, valor: str) -> QuerySet[Contacto]:
        valor = valor.strip()
        if not valor:
            return queryset
        if valor.isdigit():
            return queryset.filter(nip__startswith=valor)
        return queryset.filter(Q(nombre__icontains=valor) | Q(nip__istartswith=valor))
