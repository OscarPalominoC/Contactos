"""Paginación page[number] / page[size] con sobre data/meta/links."""

from typing import Any
from urllib.parse import urlencode

from django.core.paginator import InvalidPage, Paginator
from django.db.models import QuerySet
from rest_framework.exceptions import NotFound
from rest_framework.pagination import BasePagination
from rest_framework.request import Request
from rest_framework.response import Response

TAMANO_POR_DEFECTO = 25
TAMANO_MAXIMO = 100


class PaginacionEstandar(BasePagination):
    """page[number] (desde 1) y page[size] (máximo 100)."""

    def _entero(self, request: Request, clave: str, defecto: int) -> int:
        try:
            valor = int(request.query_params.get(clave, defecto))
        except (TypeError, ValueError):
            return defecto
        return valor if valor > 0 else defecto

    def paginate_queryset(self, queryset: QuerySet[Any], request: Request, view: Any = None) -> list[Any]:
        self.request = request
        self.tamano = min(self._entero(request, "page[size]", TAMANO_POR_DEFECTO), TAMANO_MAXIMO)
        numero = self._entero(request, "page[number]", 1)
        paginador = Paginator(queryset, self.tamano)
        try:
            self.pagina = paginador.page(numero)
        except InvalidPage as exc:
            raise NotFound("La página solicitada no existe.") from exc
        return list(self.pagina)

    def _enlace(self, numero: int | None) -> str | None:
        if numero is None:
            return None
        parametros = self.request.query_params.copy()
        parametros["page[number]"] = str(numero)
        parametros["page[size]"] = str(self.tamano)
        return f"{self.request.path}?{urlencode(sorted(parametros.items()))}"

    def get_paginated_response(self, data: Any) -> Response:
        pagina = self.pagina
        total_paginas = pagina.paginator.num_pages
        return Response(
            {
                "data": data,
                "meta": {
                    "page": {
                        "number": pagina.number,
                        "size": self.tamano,
                        "total": pagina.paginator.count,
                        "total_pages": total_paginas,
                    }
                },
                "links": {
                    "self": self._enlace(pagina.number),
                    "first": self._enlace(1),
                    "last": self._enlace(total_paginas),
                    "prev": self._enlace(pagina.previous_page_number() if pagina.has_previous() else None),
                    "next": self._enlace(pagina.next_page_number() if pagina.has_next() else None),
                },
            }
        )

    def get_paginated_response_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "data": schema,
                "meta": {"type": "object"},
                "links": {"type": "object"},
            },
        }

    def get_schema_operation_parameters(self, view: Any) -> list[dict[str, Any]]:
        return [
            {"name": "page[number]", "in": "query", "required": False, "schema": {"type": "integer", "minimum": 1}},
            {
                "name": "page[size]",
                "in": "query",
                "required": False,
                "schema": {"type": "integer", "minimum": 1, "maximum": TAMANO_MAXIMO},
            },
        ]
