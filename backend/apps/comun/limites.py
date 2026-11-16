"""Límites de peticiones (429 con Retry-After)."""

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LimiteAutenticacion(AnonRateThrottle):
    """10 peticiones por minuto por IP en login y refresh."""

    scope = "autenticacion"


class LimiteUsuario(UserRateThrottle):
    """Límite general por usuario autenticado."""

    scope = "usuario"
