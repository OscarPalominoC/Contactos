"""Errores RFC 7807 (application/problem+json)."""

import logging
from typing import Any

from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.http import Http404
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler

from apps.comun.excepciones import CambioClaveRequerido, Conflicto, DatosInvalidos
from apps.comun.middleware import request_id_actual

__all__ = ["CambioClaveRequerido", "Conflicto", "DatosInvalidos", "manejador_problemas", "problema"]

logger = logging.getLogger(__name__)

TIPO_BASE = "/problemas/"

TITULOS = {
    400: "Solicitud inválida",
    401: "No autenticado",
    403: "Prohibido",
    404: "No encontrado",
    405: "Método no permitido",
    409: "Conflicto",
    415: "Tipo de contenido no soportado",
    422: "Datos inválidos",
    429: "Demasiadas solicitudes",
    500: "Error interno",
}


def problema(
    estado: int,
    detalle: str,
    tipo: str | None = None,
    instancia: str = "",
    errores: dict[str, Any] | None = None,
) -> Response:
    """Construye una respuesta RFC 7807."""
    cuerpo: dict[str, Any] = {
        "type": TIPO_BASE + (tipo or str(estado)),
        "title": TITULOS.get(estado, "Error"),
        "status": estado,
        "detail": detalle,
        "instance": instancia,
        "request_id": request_id_actual.get(),
    }
    if errores:
        cuerpo["errors"] = errores
    return Response(cuerpo, status=estado, content_type="application/problem+json")


def _codigo(exc: exceptions.APIException) -> str:
    codigos = exc.get_codes()
    if isinstance(codigos, str):
        return codigos
    return exc.default_code


def manejador_problemas(exc: Exception, context: dict[str, Any]) -> Response | None:
    """Convierte toda excepción en un ProblemDetail sin exponer trazas ni SQL."""
    request = context.get("request")
    instancia = request.get_full_path() if request is not None else ""

    if isinstance(exc, IntegrityError):
        logger.warning("Conflicto de integridad en %s", instancia)
        return problema(409, "El registro entra en conflicto con uno existente.", "conflicto", instancia)
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()

    if isinstance(exc, exceptions.ValidationError):
        return problema(422, "Revise los campos marcados.", "datos-invalidos", instancia, errores=exc.detail)  # type: ignore[arg-type]

    respuesta = exception_handler(exc, context)
    if respuesta is None:
        logger.exception("Error no controlado en %s", instancia)
        return problema(
            500, "Ocurrió un error inesperado. Informe el request_id a soporte.", "error-interno", instancia
        )

    if not isinstance(exc, exceptions.APIException):
        return respuesta
    detalle = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    nueva = problema(respuesta.status_code, detalle, _codigo(exc), instancia)
    for cabecera in ("WWW-Authenticate", "Retry-After", "Allow"):
        if cabecera in respuesta:
            nueva[cabecera] = respuesta[cabecera]
    if respuesta.status_code == 401 and "WWW-Authenticate" not in nueva:
        nueva["WWW-Authenticate"] = 'Bearer realm="api"'
    espera = getattr(exc, "wait", None)
    if isinstance(exc, exceptions.Throttled) and espera is not None:
        nueva["Retry-After"] = str(int(espera) + 1)
    return nueva
