"""Registra los ingresos al Django Admin (exitosos y fallidos)."""

from typing import Any

from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.dispatch import receiver
from django.http import HttpRequest

from apps.cuentas.servicios import registrar_ingreso


def _es_admin(request: HttpRequest | None) -> bool:  # noqa: D103
    return request is not None and not request.path.startswith("/api/")


@receiver(user_logged_in)
def ingreso_exitoso(sender: Any, request: HttpRequest | None, user: Any, **kwargs: Any) -> None:
    if request is not None and _es_admin(request):
        registrar_ingreso(request, user.nip, exitoso=True, origen="admin")


@receiver(user_login_failed)
def ingreso_fallido(
    sender: Any, credentials: dict[str, Any], request: HttpRequest | None = None, **kwargs: Any
) -> None:
    if request is not None and _es_admin(request):
        registrar_ingreso(
            request, str(credentials.get("nip") or credentials.get("username") or ""), exitoso=False, origen="admin"
        )
