"""Autenticación JWT RS256 con `kid` y endpoint JWKS."""

import base64
import hashlib
from functools import lru_cache
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from django.conf import settings
from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.backends import TokenBackend
from rest_framework_simplejwt.exceptions import TokenBackendError
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken


def _b64(numero: int) -> str:
    datos = numero.to_bytes((numero.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(datos).rstrip(b"=").decode()


@lru_cache(maxsize=1)
def jwk_publica() -> dict[str, str]:
    clave = serialization.load_pem_public_key(settings.JWT_PUBLIC_KEY.encode())
    if not isinstance(clave, RSAPublicKey):
        raise TypeError("JWT_PUBLIC_KEY debe ser una clave RSA.")
    numeros = clave.public_numbers()
    kid = hashlib.sha256(settings.JWT_PUBLIC_KEY.encode()).hexdigest()[:16]
    return {"kty": "RSA", "use": "sig", "alg": "RS256", "kid": kid, "n": _b64(numeros.n), "e": _b64(numeros.e)}


class BackendConKid(TokenBackend):
    """Firma con RS256 incluyendo `kid` en la cabecera y rechaza cualquier otro algoritmo."""

    def encode(self, payload: dict[str, Any]) -> str:
        import jwt

        datos = payload.copy()
        if self.audience is not None:
            datos["aud"] = self.audience
        if self.issuer is not None:
            datos["iss"] = self.issuer
        return jwt.encode(
            datos,
            self.prepared_signing_key,
            algorithm=self.algorithm,
            headers={"kid": jwk_publica()["kid"]},
            json_encoder=self.json_encoder,
        )

    def decode(self, token: Any, verify: bool = True) -> dict[str, Any]:
        import jwt

        try:
            cabecera = jwt.get_unverified_header(token)
        except jwt.exceptions.DecodeError as exc:
            raise TokenBackendError("Token inválido.") from exc
        if cabecera.get("alg") != "RS256":
            raise TokenBackendError("Algoritmo no permitido.")
        return super().decode(token, verify)


@lru_cache(maxsize=1)
def backend_tokens() -> BackendConKid:
    jwt_cfg = settings.SIMPLE_JWT
    return BackendConKid(
        "RS256",
        jwt_cfg["SIGNING_KEY"],
        jwt_cfg["VERIFYING_KEY"],
        jwt_cfg["AUDIENCE"],
        jwt_cfg["ISSUER"],
    )


class AccessConKid(AccessToken):
    @property
    def token_backend(self) -> TokenBackend:
        return backend_tokens()


class RefreshConKid(RefreshToken):
    access_token_class = AccessConKid

    @property
    def token_backend(self) -> TokenBackend:
        return backend_tokens()


class AutenticacionJWT(JWTAuthentication):
    """JWT Bearer. Devuelve 401 con WWW-Authenticate: Bearer."""

    def authenticate_header(self, request: Request) -> str:
        return 'Bearer realm="api"'
