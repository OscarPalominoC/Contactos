"""Excepciones de la API (sin dependencias del manejador de errores)."""

from rest_framework import exceptions, status


class Conflicto(exceptions.APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "El recurso ya existe o entra en conflicto con otro."
    default_code = "conflicto"


class DatosInvalidos(exceptions.APIException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "Los datos enviados no son válidos."
    default_code = "datos-invalidos"


class CambioClaveRequerido(exceptions.PermissionDenied):
    default_detail = "Debe cambiar su clave temporal antes de continuar."
    default_code = "cambio-clave-requerido"


class PermisoDenegado(exceptions.PermissionDenied):
    default_detail = "No tiene permiso para realizar esta acción."
    default_code = "permiso-denegado"

