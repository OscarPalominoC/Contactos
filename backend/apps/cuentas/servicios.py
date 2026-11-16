"""Servicios de cuentas: claves temporales, cambio de clave e ingresos."""

import secrets
import string
from typing import Any

from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from apps.comun.errores import problema
from apps.cuentas.models import ClaveAnterior, Ingreso, Usuario

AMBIGUOS = set("O0Il1|")
MAYUS = [c for c in string.ascii_uppercase if c not in AMBIGUOS]
MINUS = [c for c in string.ascii_lowercase if c not in AMBIGUOS]
DIGITOS = [c for c in string.digits if c not in AMBIGUOS]
SIMBOLOS = list("#$%*+-=?@_")
LONGITUD_TEMPORAL = 16


def generar_clave_temporal(inicial: bool = False) -> str:
    """Clave temporal de 16 caracteres. Si inicial=True y existe CLAVE_TEMPORAL_INICIAL, usa dicha clave."""
    if inicial:
        from django.conf import settings

        clave_inicial = getattr(settings, "CLAVE_TEMPORAL_INICIAL", "").strip()
        if clave_inicial:
            return clave_inicial

    todos = MAYUS + MINUS + DIGITOS + SIMBOLOS
    partes = [secrets.choice(grupo) for grupo in (MAYUS, MINUS, DIGITOS, SIMBOLOS)]
    partes += [secrets.choice(todos) for _ in range(LONGITUD_TEMPORAL - len(partes))]
    secrets.SystemRandom().shuffle(partes)
    return "".join(partes)


def revocar_sesiones(usuario: Usuario) -> None:
    """Pone en lista negra todos los refresh tokens vigentes del usuario."""
    for token in OutstandingToken.objects.filter(user=usuario).exclude(blacklistedtoken__isnull=False):
        BlacklistedToken.objects.get_or_create(token=token)


@transaction.atomic
def cambiar_clave(usuario: Usuario, nueva: str) -> None:
    """Valida, guarda el hash anterior, cambia la clave y revoca las sesiones."""
    validate_password(nueva, usuario)
    if usuario.password:
        ClaveAnterior.objects.create(usuario=usuario, hash_clave=usuario.password)
    usuario.set_password(nueva)
    usuario.debe_cambiar_clave = False
    usuario.clave_cambiada_en = timezone.now()
    usuario.save(update_fields=["password", "debe_cambiar_clave", "clave_cambiada_en"])
    revocar_sesiones(usuario)


@transaction.atomic
def reiniciar_clave(usuario: Usuario, inicial: bool = False) -> str:
    """Asigna una clave temporal nueva, fuerza el cambio y revoca las sesiones. Devuelve la clave en claro una vez."""
    temporal = generar_clave_temporal(inicial=inicial)
    usuario.set_password(temporal)
    usuario.debe_cambiar_clave = True
    usuario.save(update_fields=["password", "debe_cambiar_clave"])
    revocar_sesiones(usuario)
    from axes.utils import reset

    reset(username=usuario.nip)
    return temporal


def ip_cliente(request: HttpRequest) -> str | None:
    return request.META.get("REMOTE_ADDR")


def registrar_ingreso(request: HttpRequest, nip: str, exitoso: bool, origen: str = "api") -> None:
    Ingreso.objects.create(
        fecha=timezone.now(), nip_usuario=nip[:45], ip=ip_cliente(request), exitoso=exitoso, origen=origen
    )


def respuesta_bloqueo(
    request: HttpRequest, credentials: dict[str, Any] | None = None, *args: Any, **kwargs: Any
) -> Any:
    """Respuesta de django-axes al bloquear: 429 RFC 7807 con Retry-After."""
    from django.http import JsonResponse

    from apps.comun.middleware import request_id_actual

    cuerpo = {
        "type": "/problemas/cuenta-bloqueada",
        "title": "Demasiadas solicitudes",
        "status": 429,
        "detail": "Cuenta bloqueada temporalmente por intentos fallidos. Intente en 1 hora o contacte a un administrador.",
        "instance": request.path,
        "request_id": request_id_actual.get(),
    }
    respuesta = JsonResponse(cuerpo, status=429, content_type="application/problem+json")
    respuesta["Retry-After"] = "3600"
    return respuesta


__all__ = ["cambiar_clave", "generar_clave_temporal", "problema", "registrar_ingreso", "reiniciar_clave"]
