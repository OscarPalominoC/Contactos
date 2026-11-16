"""Middleware X-Request-ID y filtros de logging."""

import logging
import re
import uuid
from collections.abc import Callable
from contextvars import ContextVar

from django.http import HttpRequest, HttpResponse

request_id_actual: ContextVar[str] = ContextVar("request_id", default="-")

PATRON_UUID = re.compile(r"^[0-9a-fA-F-]{36}$")


class RequestIdMiddleware:
    """Acepta el X-Request-ID del cliente (si es un UUID) o genera uno y lo devuelve siempre."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        recibido = request.headers.get("X-Request-ID", "")
        rid = recibido if PATRON_UUID.match(recibido) else str(uuid.uuid4())
        request.request_id = rid  # type: ignore[attr-defined]
        token = request_id_actual.set(rid)
        try:
            response = self.get_response(request)
        finally:
            request_id_actual.reset(token)
        response["X-Request-ID"] = rid
        return response


class FiltroRequestId(logging.Filter):
    """Agrega el request_id actual a cada registro de log."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_actual.get()
        return True


PATRON_CORREO = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PATRON_NUMERO_LARGO = re.compile(r"\b\d{6,}\b")


class FiltroDatosPersonales(logging.Filter):
    """Enmascara correos y números largos (cédulas, teléfonos) en los mensajes de log."""

    def filter(self, record: logging.LogRecord) -> bool:
        mensaje = record.getMessage()
        limpio = PATRON_NUMERO_LARGO.sub(lambda m: "****" + m.group()[-2:], PATRON_CORREO.sub("<correo>", mensaje))
        if limpio != mensaje:
            record.msg = limpio
            record.args = None
        return True
