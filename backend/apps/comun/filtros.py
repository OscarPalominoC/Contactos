"""Filtros filter[<campo>] y orden sort=campo,-campo con listas blancas."""

from typing import Any

from django.db.models import QuerySet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import BaseFilterBackend
from rest_framework.request import Request

from apps.comun.excepciones import DatosInvalidos


class FiltroCorchetes(DjangoFilterBackend):  # type: ignore[misc]
    """Traduce filter[campo]=valor a los filtros de django-filter. Rechaza campos fuera de la lista blanca."""

    def get_filterset_kwargs(self, request: Request, queryset: QuerySet[Any], view: Any) -> dict[str, Any]:
        datos: dict[str, str] = {}
        clase = self.get_filterset_class(view, queryset)
        permitidos = set(clase.base_filters) if clase else set()
        for clave, valor in request.query_params.items():
            if clave.startswith("filter[") and clave.endswith("]"):
                campo = clave[7:-1]
                if campo not in permitidos:
                    raise DatosInvalidos(f"Filtro no permitido: {campo}.")
                datos[campo] = str(valor)
        return {"data": datos, "queryset": queryset, "request": request}

    def get_schema_operation_parameters(self, view: Any) -> list[dict[str, Any]]:
        clase = getattr(view, "filterset_class", None)
        if clase is None:
            return []
        return [
            {"name": f"filter[{nombre}]", "in": "query", "required": False, "schema": {"type": "string"}}
            for nombre in clase.base_filters
        ]


class OrdenSort(BaseFilterBackend):
    """sort=campo,-campo con los campos declarados en `campos_orden` de la vista."""

    def filter_queryset(self, request: Request, queryset: QuerySet[Any], view: Any) -> QuerySet[Any]:
        texto = request.query_params.get("sort")
        permitidos: tuple[str, ...] = getattr(view, "campos_orden", ())
        # Un alias ordena por varias columnas, p. ej. cumpleanos → mes_nac, dia_nac.
        alias: dict[str, tuple[str, ...]] = getattr(view, "alias_orden", {})
        if not texto:
            return queryset
        orden: list[str] = []
        for parte in texto.split(","):
            campo = parte.strip()
            nombre = campo.lstrip("-")
            if nombre not in permitidos:
                raise DatosInvalidos(f"Orden no permitido: {campo}.")
            signo = "-" if campo.startswith("-") else ""
            orden.extend(f"{signo}{c}" for c in alias.get(nombre, (nombre,)))
        return queryset.order_by(*orden)

    def get_schema_operation_parameters(self, view: Any) -> list[dict[str, Any]]:
        campos: tuple[str, ...] = getattr(view, "campos_orden", ())
        if not campos:
            return []
        return [
            {
                "name": "sort",
                "in": "query",
                "required": False,
                "description": "Campos permitidos: " + ", ".join(campos) + ". Prefijo '-' para descendente.",
                "schema": {"type": "string"},
            }
        ]
