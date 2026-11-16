"""Extensiones de drf-spectacular: esquema de seguridad Bearer JWT."""

from typing import Any

from drf_spectacular.extensions import OpenApiAuthenticationExtension


class EsquemaJWT(OpenApiAuthenticationExtension):  # type: ignore[no-untyped-call]
    target_class = "apps.cuentas.autenticacion.AutenticacionJWT"
    name = "jwtBearer"

    def get_security_definition(self, auto_schema: Any) -> dict[str, str]:
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Token de acceso RS256 de 5 minutos obtenido en /api/v1/auth/login.",
        }
